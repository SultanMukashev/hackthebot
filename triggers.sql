-- SQLite
-- 1. When a transaction happens, decrease bottle amount at the point and decrease household balance
CREATE OR REPLACE FUNCTION update_bottle_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- Decrease bottle amount at the point
    UPDATE bottle_points
    SET bottle_amount = bottle_amount - NEW.bottles_charged
    WHERE point_id = NEW.point_id;

    -- Decrease household bottle balance
    UPDATE households
    SET bottle_balance = bottle_balance - NEW.bottles_charged
    WHERE id = NEW.household_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_bottle_balance
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_bottle_balance();

-- 2. When a new user is added, find the nearest bottle point automatically
CREATE OR REPLACE FUNCTION set_nearest_bottle_point()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users
    SET nearest_point = (SELECT address
                         FROM bottle_points
                         ORDER BY (ABS(latitude - NEW.n_latitude) + ABS(longitude - NEW.n_longitude))
                         LIMIT 1),
        n_latitude = (SELECT latitude
                      FROM bottle_points
                      ORDER BY (ABS(latitude - NEW.n_latitude) + ABS(longitude - NEW.n_longitude))
                      LIMIT 1),
        n_longitude = (SELECT longitude
                       FROM bottle_points
                       ORDER BY (ABS(latitude - NEW.n_latitude) + ABS(longitude - NEW.n_longitude))
                       LIMIT 1)
    WHERE id = NEW.id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_nearest_bottle_point
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION set_nearest_bottle_point();


-- 3. When a new person joins a household, increase the household bottle balance by 5
CREATE OR REPLACE FUNCTION increase_household_bottles()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE households
    SET bottle_balance = bottle_balance + 5
    WHERE id = NEW.household_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_increase_household_bottles
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION increase_household_bottles();

-- 4. Create a function to refill bottles at a point
CREATE OR REPLACE FUNCTION refill_bottle_point(employee_id_param BIGINT, point_id_param INT, amount INT)
RETURNS TEXT AS $$
DECLARE
    error_message TEXT;
BEGIN
    -- Update the bottle amount at the point
    UPDATE bottle_points
    SET bottle_amount = bottle_amount + amount
    WHERE point_id = point_id_param;

    -- Update the employee's monthly bottle count
    UPDATE emp_work
    SET bottle_per_month = bottle_per_month + amount,
        month_year = NOW()
    WHERE employee_id = employee_id_param;

    RETURN '✅ Transaction successful: Bottles transferred!';
EXCEPTION
    WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS error_message = MESSAGE_TEXT;
        RETURN '❌ Transaction failed: ' || error_message;
END;
$$ LANGUAGE plpgsql;

-- 5. Create function for getting bottles
CREATE FUNCTION transfer_bottles(household_id INT, point_id_param INT, bottles_charged INT) 
RETURNS TEXT AS $$
DECLARE
    current_balance INT;
    point_balance INT;
    error_message TEXT;
BEGIN
    -- Get the current bottle balance of the household
    SELECT bottle_balance INTO current_balance
    FROM households
    WHERE id = household_id;

    -- Get the current bottle balance of the collection point
    SELECT bottle_amount INTO point_balance
    FROM bottle_points
    WHERE point_id = point_id_param;

    -- Check if the household has enough bottles
    IF current_balance < bottles_charged THEN
        RETURN '❌ Transaction failed: Not enough bottles in household!';
    END IF;

    -- Check if the bottle point has enough bottles
    IF point_balance < bottles_charged THEN
        RETURN '❌ Transaction failed: Not enough bottles at the point!';
    END IF;

    -- Add transaction record
    INSERT INTO transactions (household_id, bottles_charged, point_id)
    VALUES (household_id, bottles_charged, point_id_param);

    RETURN '✅ Transaction successful: Bottles transferred!';
EXCEPTION
    WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS error_message = MESSAGE_TEXT;
        RETURN '❌ Transaction failed: ' || error_message;
END;
$$ LANGUAGE plpgsql;

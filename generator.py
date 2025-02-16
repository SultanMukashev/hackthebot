import qrcode

def generate_qr_code(text, file_name="qrcode.png"):
    """Generates a QR code from text and saves it as an image file."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")
    img.save(file_name) 
    print(f"QR Code saved as {file_name}")
    return file_name  
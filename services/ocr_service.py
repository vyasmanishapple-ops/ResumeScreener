def ocr_if_needed(file_path, existing_text):
    if len(existing_text.strip()) >= 100:
        return existing_text
    try:
        import pytesseract
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, dpi=180)
        return "\n".join(pytesseract.image_to_string(i) for i in images)
    except Exception:
        return existing_text

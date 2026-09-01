from paddleocr import PaddleOCR

ocr = PaddleOCR(lang="en")

result = ocr.predict("img/images.png")

for res in result:
    res.print()
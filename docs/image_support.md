# Image/Screenshot Support

## Overview
The fact-checking system now supports uploading images and screenshots (like tweets, social media posts, or any image containing text) for fact-checking.

## Supported Image Formats
- **PNG** (.png) - Best for screenshots
- **JPEG/JPG** (.jpg, .jpeg) - Common photo format
- **GIF** (.gif) - Animated or static images
- **WEBP** (.webp) - Modern web format
- **BMP** (.bmp) - Bitmap images
- **TIFF** (.tiff, .tif) - High-quality images

## Use Cases
Perfect for fact-checking:
- **Screenshots of tweets** with controversial claims
- **Social media posts** (Facebook, Instagram, etc.)
- **News article screenshots**
- **Memes with text**
- **Images of documents** (when PDF isn't available)
- **Photos of signs or posters**

## How It Works

1. **Upload**: Drag and drop or select an image file
2. **OCR Processing**: System extracts text using RapidOCR
3. **Claim Extraction**: Identifies factual claims from the extracted text
4. **Verification**: Checks claims against evidence database
5. **Results**: Shows verdicts with citations

## Technical Details

### OCR Engine
- Uses `rapidocr-onnxruntime` for fast, accurate text extraction
- Handles various image qualities and text orientations
- Optimized for screenshots and digital images

### Processing Flow
```
Image Upload → OCR Text Extraction → Claim Extraction → Verification → Results
```

### Performance
- **Small images** (< 2MB): ~5-10 seconds
- **Large images** (> 5MB): ~15-30 seconds
- **Multiple images**: Process sequentially

## Tips for Best Results

### Image Quality
- **High resolution**: Better text recognition
- **Clear text**: Avoid blurry or distorted images
- **Good contrast**: Text should stand out from background
- **Straight orientation**: Rotate images so text is horizontal

### Screenshot Best Practices
1. **Full capture**: Include all relevant text
2. **High DPI**: Use high-resolution screenshots
3. **Clean edges**: Crop unnecessary UI elements if possible
4. **Multiple screenshots**: For long tweets/posts, combine into one image or upload separately

### Common Issues

**"No text could be extracted"**
- Image may be too blurry or low quality
- Text might be too small
- Try a higher resolution screenshot

**"OCR processing failed"**
- Check image format is supported
- Ensure file isn't corrupted
- Try converting to PNG format

## Example Workflow

1. **See a controversial tweet**: Screenshot it
2. **Upload screenshot**: Drag into the fact-check tool
3. **Wait for processing**: Usually 10-30 seconds
4. **Review results**: See which claims are supported, contradicted, or need more evidence
5. **Share findings**: Use the verification results to inform discussions

## API Usage

```bash
# Upload an image
curl -X POST "http://localhost:8001/v1/documents" \
  -F "file=@screenshot.png" \
  -F "title=Twitter Screenshot" \
  -F "source_type=upload"
```

## Future Enhancements

- **Batch image upload**: Process multiple screenshots at once
- **Image preprocessing**: Auto-rotate, enhance contrast
- **Multi-language OCR**: Support for non-English text
- **Layout detection**: Better handling of complex layouts (tweets, posts)


/**
 * Utility for optimizing images before upload to the inspection backend.
 * 
 * Mobile phones often produce 10MB+ images (4000x3000px) that cause network timeouts
 * or dropped TCP sockets on cellular connections, especially when communicating with
 * cloud services waking up from cold-start.
 * 
 * This downsizes oversized images to a standard dimension (e.g. max 1600px) and
 * high-quality JPEG (0.88), reducing payload size by ~90% while keeping all text
 * sharp and readable for RapidOCR.
 */

export async function optimizeImageForUpload(
  file: File | Blob,
  maxDimension = 1600,
  quality = 0.88
): Promise<File | Blob> {
  // If file is already small (< 1MB), skip optimization
  if (file.size < 1024 * 1024) {
    return file;
  }

  // Ensure execution environment supports DOM/Canvas
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return file;
  }

  try {
    let sourceWidth = 0;
    let sourceHeight = 0;
    let imageSource: ImageBitmap | HTMLImageElement;

    if (typeof createImageBitmap === 'function') {
      try {
        const bitmap = await createImageBitmap(file);
        sourceWidth = bitmap.width;
        sourceHeight = bitmap.height;
        imageSource = bitmap;
      } catch {
        imageSource = await loadHtmlImage(file);
        sourceWidth = imageSource.width;
        sourceHeight = imageSource.height;
      }
    } else {
      imageSource = await loadHtmlImage(file);
      sourceWidth = imageSource.width;
      sourceHeight = imageSource.height;
    }

    // If dimensions already within limits and file under 2MB, keep original
    if (sourceWidth <= maxDimension && sourceHeight <= maxDimension && file.size < 2 * 1024 * 1024) {
      cleanupSource(imageSource);
      return file;
    }

    let targetWidth = sourceWidth;
    let targetHeight = sourceHeight;

    if (sourceWidth > sourceHeight && sourceWidth > maxDimension) {
      targetWidth = maxDimension;
      targetHeight = Math.round((sourceHeight * maxDimension) / sourceWidth);
    } else if (sourceHeight > maxDimension) {
      targetHeight = maxDimension;
      targetWidth = Math.round((sourceWidth * maxDimension) / sourceHeight);
    }

    const canvas = document.createElement('canvas');
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      cleanupSource(imageSource);
      return file;
    }

    // High quality rendering
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(imageSource, 0, 0, targetWidth, targetHeight);
    cleanupSource(imageSource);

    return new Promise<File | Blob>((resolve) => {
      canvas.toBlob(
        (blob) => {
          if (blob && blob.size < file.size) {
            const fileName =
              file instanceof File
                ? file.name.replace(/\.[^.]+$/, '.jpg')
                : `label_upload_${Date.now()}.jpg`;
            resolve(new File([blob], fileName, { type: 'image/jpeg' }));
          } else {
            resolve(file);
          }
        },
        'image/jpeg',
        quality
      );
    });
  } catch (err) {
    console.warn('Image optimization skipped, using original file:', err);
    return file;
  }
}

function loadHtmlImage(file: File | Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = (e) => {
      URL.revokeObjectURL(url);
      reject(e);
    };
    img.src = url;
  });
}

function cleanupSource(source: ImageBitmap | HTMLImageElement): void {
  if ('close' in source && typeof (source as ImageBitmap).close === 'function') {
    (source as ImageBitmap).close();
  }
}

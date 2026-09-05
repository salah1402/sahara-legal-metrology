import { useState, useCallback } from 'react';
import type {
  InspectionRecord,
  InspectionImage,
  InspectionPipelineStage,
} from '../types/inspection';
import { processOCR } from '../services/ocrService';
import { normalizeOCR } from '../services/normalizeService';
import { evaluateCompliance } from '../services/complianceService';
import * as inspectionService from '../services/inspectionService';
import { formatProductCompositeTitle } from '../utils/formatters';
import { showToast } from './useToast';

export function useInspection() {
  const [activeRecord, setActiveRecord] = useState<InspectionRecord | null>(null);
  const [instructionPrompt, setInstructionPrompt] = useState<string>('');
  const [selectedImages, setSelectedImages] = useState<InspectionImage[]>([]);
  const [pipelineStage, setPipelineStage] = useState<InspectionPipelineStage>('idle');
  const [pipelineProgress, setPipelineProgress] = useState<number>(0);
  const [pipelineMessage, setPipelineMessage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [activeImageIndex, setActiveImageIndex] = useState<number>(0);
  const [selectedOcrId, setSelectedOcrId] = useState<string | null>(null);
  const [hoveredOcrId, setHoveredOcrId] = useState<string | null>(null);
  const [showOcrBoxes, setShowOcrBoxes] = useState<boolean>(false);

  // Load inspection record by ID
  const loadInspection = useCallback(async (id: string) => {
    setError(null);
    setPipelineStage('idle');
    try {
      const record = await inspectionService.getInspection(id);
      if (record) {
        setActiveRecord(record);
        setInstructionPrompt(record.instructionPrompt || '');
        setSelectedImages(record.images || []);
        setActiveImageIndex(0);
        setSelectedOcrId(null);
      } else {
        showToast('error', 'Not Found', `Inspection record ${id} could not be located.`);
      }
    } catch (e: any) {
      showToast('error', 'Load Failed', e.message || 'Error loading inspection record.');
    }
  }, []);

  // Reset workspace to fresh inspection
  const resetToNew = useCallback(() => {
    setActiveRecord(null);
    setInstructionPrompt('');
    setSelectedImages([]);
    setPipelineStage('idle');
    setPipelineProgress(0);
    setPipelineMessage('');
    setError(null);
    setActiveImageIndex(0);
    setSelectedOcrId(null);
  }, []);

  // Add files to current inspection draft
  const addImages = useCallback(async (files: File[]) => {
    const validExtensions = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
    const maxSizeBytes = 20 * 1024 * 1024; // 20 MB

    const newImages: InspectionImage[] = [];

    for (const file of files) {
      if (!validExtensions.includes(file.type.toLowerCase())) {
        showToast('error', 'Unsupported Format', `${file.name} is not a valid JPEG, PNG, or WEBP image.`);
        continue;
      }

      if (file.size > maxSizeBytes) {
        showToast('error', 'File Too Large', `${file.name} exceeds the 20MB limit.`);
        continue;
      }

      const previewUrl = URL.createObjectURL(file);
      const imgId = `img_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`;

      newImages.push({
        id: imgId,
        name: file.name,
        size: file.size,
        type: file.type,
        previewUrl,
        uploadedAt: new Date().toISOString(),
      });
    }

    if (newImages.length > 0) {
      setSelectedImages(prev => [...prev, ...newImages]);
      showToast('success', 'Image Added', `Added ${newImages.length} image(s) to inspection.`);
    }
  }, []);

  // Remove image
  const removeImage = useCallback((id: string) => {
    setSelectedImages(prev => {
      const filtered = prev.filter(img => img.id !== id);
      if (activeImageIndex >= filtered.length) {
        setActiveImageIndex(Math.max(0, filtered.length - 1));
      }
      return filtered;
    });
  }, [activeImageIndex]);

  // Reorder images
  const reorderImages = useCallback((newImages: InspectionImage[]) => {
    setSelectedImages(newImages);
  }, []);

  // Execute OCR -> Nemotron normalization pipeline
  const startInspection = useCallback(async () => {
    if (selectedImages.length === 0) {
      showToast('warning', 'No Images', 'Please upload or capture at least one product label photo.');
      return;
    }

    setError(null);

    try {
      // Stage 1: Preparing image
      setPipelineStage('preparing_image');
      setPipelineProgress(25);
      setPipelineMessage('Preparing image buffer for upload...');

      const targetImage = selectedImages[0];
      const res = await fetch(targetImage.previewUrl);
      const blob = await res.blob();
      const imageFile = new File([blob], targetImage.name, { type: targetImage.type || 'image/jpeg' });

      // Stage 2: Processing OCR with RapidOCR backend
      setPipelineStage('processing_ocr');
      setPipelineProgress(50);
      setPipelineMessage('Running RapidOCR detection and text recognition on backend...');

      const ocrData = await processOCR(imageFile);

      // Stage 3: NVIDIA Nemotron Semantic Normalization
      setPipelineStage('understanding_label');
      setPipelineProgress(80);
      setPipelineMessage('Normalizing OCR observations via NVIDIA Nemotron 3 Ultra 550B...');

      const normalizedData = await normalizeOCR(ocrData.inspection_id, ocrData.ocr);

      // Stage 4: Legal Metrology Compliance Engine (Phase 3)
      setPipelineStage('evaluating_compliance');
      setPipelineProgress(90);
      setPipelineMessage('Evaluating Legal Metrology (PCR 2011) statutory compliance...');

      let complianceData = undefined;
      let finalStatus: any = 'Structured Data Ready';

      try {
        complianceData = await evaluateCompliance(ocrData.inspection_id);
        if (complianceData.overall_status === 'COMPLIANT') {
          finalStatus = 'Compliant';
        } else if (complianceData.overall_status === 'NON_COMPLIANT') {
          finalStatus = 'Non-Compliant';
        } else {
          finalStatus = 'Needs Review';
        }
      } catch (compErr) {
        console.warn('Compliance evaluation warning:', compErr);
      }

      // Stage 5: Complete
      setPipelineStage('complete');
      setPipelineProgress(100);
      setPipelineMessage('Legal Metrology compliance assessment complete.');

      const derivedTitle = (() => {
        if (instructionPrompt && instructionPrompt.trim()) {
          return instructionPrompt.trim();
        }
        const comm = normalizedData.product?.commodity_name?.status === 'extracted' ? normalizedData.product.commodity_name.value : undefined;
        const brand = normalizedData.product?.manufacturer?.status === 'extracted' ? normalizedData.product.manufacturer.value : undefined;
        return formatProductCompositeTitle(comm, brand, targetImage.name);
      })();

      const newRecord: InspectionRecord = {
        id: ocrData.inspection_id,
        metadata: {
          inspection_id: ocrData.inspection_id,
          display_name: instructionPrompt && instructionPrompt.trim() ? instructionPrompt.trim() : undefined,
          product_name: derivedTitle,
          created_at: ocrData.created_at || new Date().toISOString(),
          category: 'Packaged Commodity',
          image_count: selectedImages.length,
          status: finalStatus,
          notes: `Extracted ${ocrData.ocr.length} OCR tokens. Normalized with NVIDIA Nemotron. Evaluated under PCR 2011.`,
        },
        instructionPrompt: instructionPrompt || '',
        images: selectedImages,
        ocrResult: {
          inspection_id: ocrData.inspection_id,
          engine: ocrData.engine || 'RapidOCR',
          images: [
            {
              image_id: targetImage.id,
              ocr: ocrData.ocr
            }
          ]
        },
        normalized: normalizedData,
        compliance: complianceData
      };

      // Persist to local storage & history
      await inspectionService.saveInspection(newRecord);
      setActiveRecord(newRecord);
      showToast('success', 'Normalization Completed', `${ocrData.inspection_id} structured successfully`);
    } catch (err: any) {
      console.error('Inspection failed:', err);
      setPipelineStage('error');
      const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
      const fallbackMsg = isLocal
        ? 'Unable to connect to the local development backend. Make sure your local FastAPI server is running.'
        : 'Unable to connect to the SAHARA inspection backend. The cloud service may be waking up from sleep; please try again in a few seconds.';
      const errorMsg = err.message || fallbackMsg;
      setError(errorMsg);
      showToast('error', 'Normalization Pipeline Failed', errorMsg);
    }
  }, [selectedImages, instructionPrompt]);

  return {
    activeRecord,
    instructionPrompt,
    setInstructionPrompt,
    selectedImages,
    pipelineStage,
    pipelineProgress,
    pipelineMessage,
    error,
    activeImageIndex,
    setActiveImageIndex,
    selectedOcrId,
    setSelectedOcrId,
    hoveredOcrId,
    setHoveredOcrId,
    showOcrBoxes,
    setShowOcrBoxes,
    addImages,
    removeImage,
    reorderImages,
    startInspection,
    loadInspection,
    resetToNew,
  };
}

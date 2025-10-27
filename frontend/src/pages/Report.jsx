import { useMemo, useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";

// ✅ Stepper component
function Stepper({ step }) {
  const items = [
    "Prescription OCR", 
    "Scan Region Select", 
    "Overall Report"
  ];

  return (
    <ol className="flex flex-wrap gap-3">
      {items.map((label, idx) => {
        const active = step === idx;
        const done = step > idx;
        return (
          <li
            key={label}
            className={`flex items-center gap-2 px-3 py-1 rounded-full border text-sm ${
              active
                ? "border-vibrant-blue text-vibrant-blue bg-blue-50"
                : done
                ? "border-green-300 text-green-700 bg-green-50"
                : "border-gray-200 text-gray-600 bg-white"
            }`}
          >
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                active
                  ? "bg-vibrant-blue text-white"
                  : done
                  ? "bg-green-500 text-white"
                  : "bg-gray-200 text-gray-700"
              }`}
            >
              {idx + 1}
            </span>
            {label}
          </li>
        );
      })}
    </ol>
  );
}

function Reports() {
  const navigate = useNavigate();
  const location = useLocation();
  
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  
  // Extract pseudonym_id from URL or location state
  // Extract pseudonym_id from the URL path, e.g. /reports/P-1283-9D93
  const pathParts = location.pathname.split("/");
  const pseudonym_id = pathParts[pathParts.length - 1] || location.state?.pseudonym_id;

  const initialPrescriptionOCR = useMemo(
    () =>
      `Dr. Sarah Mitchell, MD
Cardiology Department
City General Hospital

Patient: Alex Johnson
Age: 54 | Gender: Male
Date: October 25, 2024

Chief Complaint: Chronic right knee pain with swelling

Prescription:
1. Ibuprofen 400mg - Take 1 tablet twice daily with food for pain
2. Glucosamine 1500mg - Take 1 tablet daily for joint health
3. Omeprazole 20mg - Take 1 tablet daily before breakfast (for gastric protection)

Instructions:
- Continue current physiotherapy sessions (3x per week)
- Apply ice pack to affected area for 15-20 minutes, 3 times daily
- Avoid high-impact activities (running, jumping)
- Use knee brace during physical activities

Follow-up: Schedule appointment in 4 weeks

Dr. Sarah Mitchell
License #: MD-12345-NY`,
    []
  );

  // Sample medical scan images - will be replaced with actual data from backend
  const [sampleImages, setSampleImages] = useState([
    {
      id: 1,
      url: "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTpqQRADz6LD9XBSjZq9EqqAQrEfg9kCrir4w&s",
      name: "Chest X-Ray",
    }
  ]);

  const [step, setStep] = useState(0);
  const [prescriptionOCR, setPrescriptionOCR] = useState(initialPrescriptionOCR);
  const [pathologyOCR, setPathologyOCR] = useState();
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [imageRegions, setImageRegions] = useState({});
  const [redoStack, setRedoStack] = useState({});
  const [regionAnalysis, setRegionAnalysis] = useState("");
  const [overallReport, setOverallReport] = useState("");
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [savedReportId, setSavedReportId] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch intake form data on component mount
  useEffect(() => {
    const fetchIntakeFormData = async () => {
      if (!pseudonym_id) {
        console.error("No pseudonym_id provided");
        setLoading(false);
        return;
      }

      try {
        const token = localStorage.getItem('token');
        const response = await fetch(
          `${API_BASE_URL}/report/intake-form/${pseudonym_id}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch intake form data: ${response.statusText}`);
        }

        const data = await response.json();
        console.log("Fetched intake form data:", data);

        // Update prescription OCR if available
        if (data.prescription_ocr) {
          setPrescriptionOCR(data.prescription_ocr);
        }

        // Store pathology OCR
        if (data.pathology_ocr) {
          setPathologyOCR(data.pathology_ocr);
        }

        // Update scan images if available (flag whether entry is an image)
        if (data.scan_images && data.scan_images.length > 0) {
          // map possible URL fields and conservative image flag based on extension
          const mapped = data.scan_images.map((img, index) => {
            const url = img.url || img.http_url || img.uri || img.presigned_url || "";
            return {
              id: index + 1,
              url,
              name: img.name || img.original_filename || `Scan ${index + 1}`,
            };
          });

          console.log("Mapped scan images:", mapped);
          setSampleImages(mapped);
          console.log(sampleImages);
        }

        setLoading(false);
      } catch (error) {
        console.error("Error fetching intake form data:", error);
        setLoading(false);
      }
    };

    fetchIntakeFormData();
  }, [pseudonym_id, API_BASE_URL]);

  const canvasRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [startPos, setStartPos] = useState(null);

  const currentImage = sampleImages[currentImageIndex];
  const selectedRegions = imageRegions[currentImage?.id] || [];

  // Generate region analysis when moving to step 3
  useEffect(() => {
    if (step === 3 && !regionAnalysis) {
      generateRegionAnalysis();
    }
  }, [step]);

  // Generate overall report when moving to step 4
  useEffect(() => {
    if (step === 2 && !overallReport) {
      generateOverallReport();
    }
  }, [step]);

  const generateRegionAnalysis = () => {
    const totalRegions = getTotalRegions();
    const imagesWithRegions = Object.keys(imageRegions).length;
    
    let analysis = `REGION ANALYSIS REPORT\n`;
    analysis += `Generated: ${new Date().toLocaleString()}\n\n`;
    analysis += `Summary:\n`;
    analysis += `- Total scans analyzed: ${imagesWithRegions}\n`;
    analysis += `- Total regions of interest marked: ${totalRegions}\n\n`;
    
    Object.entries(imageRegions).forEach(([imageId, regions]) => {
      const image = sampleImages.find(img => img.id === parseInt(imageId));
      if (regions.length > 0) {
        analysis += `${image.name}:\n`;
        regions.forEach((region, idx) => {
          analysis += `  Region ${idx + 1}: Area of concern detected at coordinates (${Math.round(region.x)}, ${Math.round(region.y)})\n`;
          analysis += `    - Dimensions: ${Math.round(region.w)}x${Math.round(region.h)} pixels\n`;
          analysis += `    - Clinical significance: Requires radiologist review\n`;
        });
        analysis += `\n`;
      }
    });
    
    analysis += `Recommendation: All marked regions should be reviewed by a specialist for detailed assessment.`;
    
    setRegionAnalysis(analysis);
  };

  const generateOverallReport = () => {
    let report = `COMPREHENSIVE MEDICAL REPORT\n`;
    report += `Patient: Alex Johnson\n`;
    report += `Report Date: ${new Date().toLocaleDateString()}\n`;
    report += `Report ID: RPT-${Date.now()}\n\n`;
    
    report += `═══════════════════════════════════════\n`;
    report += `1. PRESCRIPTION SUMMARY\n`;
    report += `═══════════════════════════════════════\n`;
    report += `Current medications prescribed for chronic knee pain management.\n`;
    report += `Key medications: Ibuprofen (anti-inflammatory), Glucosamine (joint support)\n\n`;
    
    report += `═══════════════════════════════════════\n`;
    report += `2. LABORATORY FINDINGS\n`;
    report += `═══════════════════════════════════════\n`;
    report += `⚠️ NOTABLE FINDINGS:\n`;
    report += `- Elevated C-Reactive Protein (8.5 mg/L) - indicates active inflammation\n`;
    report += `- Elevated ESR (22 mm/hr) - supports inflammatory condition\n`;
    report += `- Blood count and lipid profile within normal limits\n\n`;
    
    report += `═══════════════════════════════════════\n`;
    report += `3. IMAGING ANALYSIS\n`;
    report += `═══════════════════════════════════════\n`;
    report += `Total scans reviewed: ${Object.keys(imageRegions).length}\n`;
    report += `Regions of interest identified: ${getTotalRegions()}\n`;
    report += `All marked regions require specialist evaluation.\n\n`;
    
    report += `═══════════════════════════════════════\n`;
    report += `4. CLINICAL ASSESSMENT\n`;
    report += `═══════════════════════════════════════\n`;
    report += `The patient presents with:\n`;
    report += `- Chronic inflammatory condition (confirmed by lab markers)\n`;
    report += `- Multiple areas of concern on imaging studies\n`;
    report += `- Currently on appropriate anti-inflammatory therapy\n\n`;
    
    report += `═══════════════════════════════════════\n`;
    report += `5. RECOMMENDATIONS\n`;
    report += `═══════════════════════════════════════\n`;
    report += `1. Continue current medication regimen\n`;
    report += `2. Specialist consultation for imaging findings\n`;
    report += `3. Follow-up inflammatory markers in 4 weeks\n`;
    report += `4. Consider additional imaging if symptoms persist\n`;
    report += `5. Maintain physiotherapy and lifestyle modifications\n\n`;
    
    report += `Report compiled by: MedicoTourism AI System\n`;
    report += `Status: Pending physician review and approval\n`;
    
    setOverallReport(report);
  };

  // ✅ Load and draw image on canvas
  useEffect(() => {
    if (step !== 1 || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.crossOrigin = "anonymous";
    
    img.onload = () => {
      const maxWidth = 800;
      const scale = Math.min(1, maxWidth / img.width);
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;

      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      const regions = imageRegions[currentImage.id] || [];
      regions.forEach((r) => {
        ctx.strokeStyle = "#2563eb";
        ctx.lineWidth = 3;
        ctx.strokeRect(r.x, r.y, r.w, r.h);
        ctx.fillStyle = "rgba(37,99,235,0.2)";
        ctx.fillRect(r.x, r.y, r.w, r.h);
      });

      setImageLoaded(true);
    };

    img.onerror = (ev) => {
      console.error("Image failed to load:", currentImage?.url, ev);
      canvas.width = 600;
      canvas.height = 400;
      ctx.fillStyle = "#f1f5f9";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#64748b";
      ctx.font = "16px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Image not available", canvas.width / 2, canvas.height / 2);
      setImageLoaded(false);
    };

    img.src = currentImage.url;

    return () => {
      setImageLoaded(false);
    };
  }, [step, currentImageIndex, imageRegions, currentImage]);

  useEffect(() => {
    if (step !== 1 || !canvasRef.current || !imageLoaded) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.crossOrigin = "anonymous";

    img.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      selectedRegions.forEach((r) => {
        ctx.strokeStyle = "#2563eb";
        ctx.lineWidth = 3;
        ctx.strokeRect(r.x, r.y, r.w, r.h);
        ctx.fillStyle = "rgba(37,99,235,0.2)";
        ctx.fillRect(r.x, r.y, r.w, r.h);
      });
    };

    img.src = currentImage.url;
  }, [selectedRegions, imageLoaded, currentImage, step]);

  const handleMouseDown = (e) => {
    if (step !== 1 || !imageLoaded) return;
    const rect = canvasRef.current.getBoundingClientRect();
    setStartPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setDrawing(true);
  };

  const handleMouseMove = (e) => {
    if (!drawing || step !== 1 || !imageLoaded) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      selectedRegions.forEach((r) => {
        ctx.strokeStyle = "#2563eb";
        ctx.lineWidth = 3;
        ctx.strokeRect(r.x, r.y, r.w, r.h);
        ctx.fillStyle = "rgba(37,99,235,0.2)";
        ctx.fillRect(r.x, r.y, r.w, r.h);
      });

      ctx.strokeStyle = "#ef4444";
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.strokeRect(
        Math.min(startPos.x, currentX),
        Math.min(startPos.y, currentY),
        Math.abs(currentX - startPos.x),
        Math.abs(currentY - startPos.y)
      );
      ctx.setLineDash([]);
    };
    img.src = currentImage.url;
  };

  const handleMouseUp = (e) => {
    if (!drawing || step !== 1 || !imageLoaded) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const endX = e.clientX - rect.left;
    const endY = e.clientY - rect.top;
    const newRegion = {
      x: Math.min(startPos.x, endX),
      y: Math.min(startPos.y, endY),
      w: Math.abs(endX - startPos.x),
      h: Math.abs(endY - startPos.y),
    };
    if (newRegion.w > 5 && newRegion.h > 5) {
      setImageRegions((prev) => ({
        ...prev,
        [currentImage.id]: [...(prev[currentImage.id] || []), newRegion]
      }));
      setRedoStack((prev) => ({
        ...prev,
        [currentImage.id]: []
      }));
    }
    setDrawing(false);
  };

  const handleUndo = () => {
    const regions = imageRegions[currentImage.id] || [];
    if (regions.length === 0) return;
    const last = regions[regions.length - 1];
    setImageRegions((prev) => ({
      ...prev,
      [currentImage.id]: regions.slice(0, -1)
    }));
    setRedoStack((prev) => ({
      ...prev,
      [currentImage.id]: [...(prev[currentImage.id] || []), last]
    }));
  };

  const handleRedo = () => {
    const redos = redoStack[currentImage.id] || [];
    if (redos.length === 0) return;
    const last = redos[redos.length - 1];
    setRedoStack((prev) => ({
      ...prev,
      [currentImage.id]: redos.slice(0, -1)
    }));
    setImageRegions((prev) => ({
      ...prev,
      [currentImage.id]: [...(prev[currentImage.id] || []), last]
    }));
  };

  const handleClearRegions = () => {
    setImageRegions((prev) => ({
      ...prev,
      [currentImage.id]: []
    }));
    setRedoStack((prev) => ({
      ...prev,
      [currentImage.id]: []
    }));
  };

  const getTotalRegions = () => {
    return Object.values(imageRegions).reduce((sum, regions) => sum + regions.length, 0);
  };

  const buildPayloadForMedGemma = () => {
    // Compose image list with regions in pixel coordinates
    const images = (sampleImages || []).map((img) => {
      const regions = (imageRegions[img.id] || []).map((r) => ({
        x: Math.round(r.x),
        y: Math.round(r.y),
        w: Math.round(r.w),
        h: Math.round(r.h),
      }));
      return { url: img.url, regions };
    });
    return {
      images,
      prescription_text: prescriptionOCR || "",
      pathology_text: pathologyOCR || "",
      doctor_prompt: "Please analyze the selected regions and summarize clinical findings.",
    };
  };

  // Function to save analysis to MongoDB
  const saveAnalysisToDb = async () => {
    if (!pseudonym_id) return;
    setProcessing(true);

    try {
      const token = localStorage.getItem('token');
      const payload = {
        pseudonym_id,
        prescription_ocr: prescriptionOCR,
        pathology_ocr: pathologyOCR,
        medgemma_analysis: overallReport,
        images: sampleImages.map(img => ({
          url: img.url,
          name: img.name,
          regions: imageRegions[img.id] || []
        })),
        meta: {
          step_completed: step,
          timestamp: new Date().toISOString()
        }
      };

      const response = await fetch(`${API_BASE_URL}/report/save-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save analysis');
      }

      const data = await response.json();
      setSavedReportId(data.report_id);
      setProcessing(false);
      setSubmitted(true);

    } catch (err) {
      console.error('Failed to save analysis:', err);
      setAnalysisError(err.message || 'Failed to save analysis');
    }
  };

  // Update analyzeWithMedGemma to save results after analysis
  const analyzeWithMedGemma = async () => {
    try {
      setAnalysisLoading(true);
      setAnalysisError("");
      
      const token = localStorage.getItem("token");
      const payload = buildPayloadForMedGemma();

      const resp = await fetch(`${API_BASE_URL}/report/analyze_medgemma`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Status ${resp.status}`);
      }

      const data = await resp.json();
      if (data && data.analysis) {
        setOverallReport(String(data.analysis));
      } else {
        setOverallReport("No analysis returned from model.");
      }
    } catch (err) {
      console.error("MedGemma analysis failed:", err);
      setOverallReport("Analysis failed: " + (err.message || "unknown error"));
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Trigger analysis when user navigates to Overall Report step (index 2)
  useEffect(() => {
    if (step === 2) {
      analyzeWithMedGemma();
    }
  }, [step]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-3xl font-extrabold text-gray-900">
            Medical Reports Review
          </h1>
          <Stepper step={step} />
        </div>

        <div className="mt-6 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-sm p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-96">
              <div className="text-xl font-semibold text-gray-800 mb-4">
                Loading intake form data...
              </div>
              <div className="w-16 h-16 border-4 border-vibrant-blue border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : processing ? (
            <div className="flex flex-col items-center justify-center h-96">
              <div className="text-xl font-semibold text-gray-800 mb-4">
                Processing your comprehensive report...
              </div>
              <div className="w-16 h-16 border-4 border-vibrant-blue border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : submitted ? (
            <div className="flex flex-col items-center justify-center h-96 text-center">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <svg className="w-12 h-12 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-semibold text-green-700 mb-3">
                ✅ Comprehensive Report Generated Successfully!
              </h2>
              <p className="text-gray-600 mb-2">
                Total regions analyzed: <strong>{getTotalRegions()}</strong>
              </p>
              <p className="text-gray-600 mb-6">
                You can now chat with our AI assistant for detailed medical insights.
              </p>
              <button
                onClick={() =>
                  navigate(`/Chatbot/${pseudonym_id}`, { 
                    state: { 
                      prescriptionOCR, 
                      pathologyOCR, 
                      regionAnalysis, 
                      overallReport,
                      imageRegions 
                    } 
                  })
                }
                className="px-6 py-3 rounded-xl text-white text-lg font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-110 transition shadow-lg"
              >
                Go to AI Chatbot 💬
              </button>
            </div>
          ) : (
            <>
              <div className="mt-4">
                {/* Step 0: Prescription OCR */}
                {step === 0 && (
                  <div>
                    <div className="mb-4">
                      <h2 className="text-xl font-bold text-gray-900 mb-2">📋 Prescription OCR</h2>
                      <p className="text-sm text-gray-600">Review and edit the extracted prescription text</p>
                    </div>
                    <textarea
                      value={prescriptionOCR}
                      onChange={(e) => setPrescriptionOCR(e.target.value)}
                      className="w-full h-96 p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-vibrant-blue font-mono text-sm"
                      placeholder="Prescription details will appear here..."
                    />
                  </div>
                )}

                {/* Step 1: Scan Region Select */}
                {step === 1 && (
                  <div className="flex flex-col items-center gap-4">
                    <div className="mb-4 text-center">
                      <h2 className="text-xl font-bold text-gray-900 mb-2">🔍 Medical Scan Region Selection</h2>
                      <p className="text-sm text-gray-600">Mark regions of interest on the medical scans</p>
                    </div>

                    <div className="w-full flex items-center justify-between bg-gray-50 p-4 rounded-lg">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => setCurrentImageIndex((prev) => Math.max(0, prev - 1))}
                          disabled={currentImageIndex === 0}
                          className="px-3 py-2 rounded-lg border border-gray-300 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition"
                        >
                          ← Previous
                        </button>
                        <div className="text-sm font-medium text-gray-700">
                          <span className="text-vibrant-blue font-bold">{currentImage.name}</span>
                          <span className="text-gray-500 ml-2">
                            ({currentImageIndex + 1} of {sampleImages.length})
                          </span>
                        </div>
                        <button
                          onClick={() => setCurrentImageIndex((prev) => Math.min(sampleImages.length - 1, prev + 1))}
                          disabled={currentImageIndex === sampleImages.length - 1}
                          className="px-3 py-2 rounded-lg border border-gray-300 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition"
                        >
                          Next →
                        </button>
                      </div>
                      <div className="text-sm text-gray-600">
                        Regions on this image: <strong>{selectedRegions.length}</strong>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={handleUndo}
                        disabled={selectedRegions.length === 0}
                        className="text-sm px-4 py-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                      >
                        ↩ Undo
                      </button>
                      <button
                        onClick={handleRedo}
                        disabled={(redoStack[currentImage.id] || []).length === 0}
                        className="text-sm px-4 py-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                      >
                        ↪ Redo
                      </button>
                      <button
                        onClick={handleClearRegions}
                        disabled={selectedRegions.length === 0}
                        className="text-sm px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                      >
                        🗑️ Clear All
                      </button>
                    </div>

                    <div className="relative border-2 border-gray-300 rounded-lg overflow-hidden shadow-lg">
                      {!imageLoaded && (
                        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                          <div className="text-gray-500">Loading image...</div>
                        </div>
                      )}

                        <canvas
                          ref={canvasRef}
                          onMouseDown={handleMouseDown}
                          onMouseMove={handleMouseMove}
                          onMouseUp={handleMouseUp}
                          onMouseLeave={() => setDrawing(false)}
                          className="cursor-crosshair bg-white"
                        />
                    </div>

                    <p className="text-xs text-gray-500 text-center">
                      💡 Click and drag to select regions of interest on the scan
                    </p>
                  </div>
                )}

                {/* Step 2: Overall Report */}
                {step === 2 && (
                  <div>
                    <div className="mb-4">
                      <h2 className="text-xl font-bold text-gray-900 mb-2">📄 Comprehensive Medical Report</h2>
                      <p className="text-sm text-gray-600">Complete analysis combining all medical data</p>
                    </div>
                    <textarea
                      value={overallReport}
                      onChange={(e) => setOverallReport(e.target.value)}
                      className="w-full h-96 p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-vibrant-blue font-mono text-sm bg-green-50"
                      placeholder="Overall report will be generated automatically..."
                    />
                    {analysisLoading && <div className="text-sm text-gray-600 mt-2">Analyzing images... please wait.</div>}
                    <div className="mt-4 grid grid-cols-3 gap-4">
                      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-center">
                        <div className="text-2xl font-bold text-vibrant-blue">{getTotalRegions()}</div>
                        <div className="text-xs text-gray-600 mt-1">Regions Analyzed</div>
                      </div>
                      <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-center">
                        <div className="text-2xl font-bold text-green-600">{Object.keys(imageRegions).length}</div>
                        <div className="text-xs text-gray-600 mt-1">Scans Reviewed</div>
                      </div>
                      <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg text-center">
                        <div className="text-2xl font-bold text-purple-600">3</div>
                        <div className="text-xs text-gray-600 mt-1">Steps Completed</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  onClick={() => setStep((s) => Math.max(0, s - 1))}
                  disabled={step === 0}
                >
                  ← Back
                </button>
                <div className="flex gap-3">
                  {step < 2 ? (
                    <button
                      className="px-4 py-2 rounded-lg text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition shadow"
                      onClick={() => setStep((s) => s + 1)}
                    >
                      Next →
                    </button>
                  ) : (
                    <button
                      className="px-6 py-2 rounded-lg text-white bg-gradient-to-r from-green-500 to-teal-500 hover:brightness-105 transition shadow-lg font-semibold"
                      onClick={saveAnalysisToDb}
                    >
                      ✓ Confirm & Submit Report
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Reports;
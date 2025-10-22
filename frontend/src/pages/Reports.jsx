import { useMemo, useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";

// ✅ Stepper component
function Stepper({ step }) {
  const items = [
    "OCR & Edit",
    "Scan Region Select",
    "Model Output Edit",
    "Final Review",
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

  const initialOCR = useMemo(
    () =>
      `Patient: Alex Johnson
Age: 54
Complaint: Chronic right knee pain
Rx: Ibuprofen 400mg BID prn pain
Advice: Physio, knee brace, weight management`,
    []
  );

  const [step, setStep] = useState(0);
  const [ocrText, setOcrText] = useState(initialOCR);
  const [selectedRegions, setSelectedRegions] = useState([]);
  const [redoStack, setRedoStack] = useState([]);
  const [modelOutput, setModelOutput] = useState(
    "Likely osteoarthritis. Consider MRI to evaluate cartilage. Recommend minimally invasive knee replacement pending clearance."
  );
  const [finalNotes, setFinalNotes] = useState(
    "Combined OCR + imaging findings suggest OA; proceed with ortho referral and physio plan."
  );

  const [processing, setProcessing] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const canvasRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [startPos, setStartPos] = useState(null);

  // ✅ Draw canvas + boxes
  useEffect(() => {
    if (!canvasRef.current) return;
    const ctx = canvasRef.current.getContext("2d");
    ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);

    const size = 20;
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    ctx.strokeStyle = "#e2e8f0";

    // Grid
    for (let x = 0; x < canvasRef.current.width; x += size) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvasRef.current.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvasRef.current.height; y += size) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvasRef.current.width, y);
      ctx.stroke();
    }

    // Regions
    selectedRegions.forEach((r) => {
      ctx.strokeStyle = "#2563eb";
      ctx.lineWidth = 2;
      ctx.strokeRect(r.x, r.y, r.w, r.h);
      ctx.fillStyle = "rgba(37,99,235,0.1)";
      ctx.fillRect(r.x, r.y, r.w, r.h);
    });
  }, [selectedRegions, step]);

  const handleMouseDown = (e) => {
    if (step !== 1) return;
    const rect = canvasRef.current.getBoundingClientRect();
    setStartPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setDrawing(true);
  };

  const handleMouseUp = (e) => {
    if (!drawing || step !== 1) return;
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
      setSelectedRegions((prev) => [...prev, newRegion]);
      setRedoStack([]);
    }
    setDrawing(false);
  };

  // ✅ Undo / Redo handlers
  const handleUndo = () => {
    if (selectedRegions.length === 0) return;
    const last = selectedRegions[selectedRegions.length - 1];
    setSelectedRegions(selectedRegions.slice(0, -1));
    setRedoStack([...redoStack, last]);
  };

  const handleRedo = () => {
    if (redoStack.length === 0) return;
    const last = redoStack[redoStack.length - 1];
    setRedoStack(redoStack.slice(0, -1));
    setSelectedRegions([...selectedRegions, last]);
  };

  const handleConfirm = () => {
    setProcessing(true);
    setTimeout(() => {
      setProcessing(false);
      setSubmitted(true);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-3xl font-extrabold text-gray-900">
            Reports Review
          </h1>
          <Stepper step={step} />
        </div>

        <div className="mt-6 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-sm p-6">
          {processing ? (
            <div className="flex flex-col items-center justify-center h-96">
              <div className="text-xl font-semibold text-gray-800 mb-4">
                Processing your report...
              </div>
              <div className="w-16 h-16 border-4 border-vibrant-blue border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : submitted ? (
            <div className="flex flex-col items-center justify-center h-96 text-center">
              <h2 className="text-2xl font-semibold text-green-700 mb-3">
                ✅ Your report has been submitted successfully!
              </h2>
              <p className="text-gray-600 mb-6">
                You can now chat with our AI assistant for further insights.
              </p>
              <button
                onClick={() =>
                  navigate("/Chatbot", { state: { ocrText, modelOutput, finalNotes } })
                }
                className="px-6 py-3 rounded-xl text-white text-lg font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-110 transition"
              >
                Go to AI Chatbot 💬
              </button>
            </div>
          ) : (
            <>
              <div className="mt-4">
                {step === 0 && (
                  <textarea
                    value={ocrText}
                    onChange={(e) => setOcrText(e.target.value)}
                    className="w-full h-64 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-vibrant-blue"
                  />
                )}
                {step === 1 && (
                  <div className="flex flex-col items-center gap-3">
                    <div className="flex gap-2">
                      <button
                        onClick={handleUndo}
                        className="text-sm px-3 py-1 border rounded-lg hover:bg-gray-50"
                      >
                        Undo ↩
                      </button>
                      <button
                        onClick={handleRedo}
                        className="text-sm px-3 py-1 border rounded-lg hover:bg-gray-50"
                      >
                        Redo ↪
                      </button>
                    </div>
                    <canvas
                      ref={canvasRef}
                      width={600}
                      height={400}
                      onMouseDown={handleMouseDown}
                      onMouseUp={handleMouseUp}
                      className="border border-gray-300 rounded-lg bg-white cursor-crosshair"
                    />
                  </div>
                )}
                {step === 2 && (
                  <textarea
                    value={modelOutput}
                    onChange={(e) => setModelOutput(e.target.value)}
                    className="w-full h-64 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-vibrant-blue"
                  />
                )}
                {step === 3 && (
                  <textarea
                    value={finalNotes}
                    onChange={(e) => setFinalNotes(e.target.value)}
                    className="w-full h-64 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-vibrant-blue"
                  />
                )}
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50"
                  onClick={() => setStep((s) => Math.max(0, s - 1))}
                  disabled={step === 0}
                >
                  Back
                </button>
                <div className="flex gap-3">
                  {step < 3 ? (
                    <button
                      className="px-4 py-2 rounded-lg text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105"
                      onClick={() => setStep((s) => s + 1)}
                    >
                      Next
                    </button>
                  ) : (
                    <button
                      className="px-4 py-2 rounded-lg text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105"
                      onClick={handleConfirm}
                    >
                      Confirm
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

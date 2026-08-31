// app/predict/page.tsx
// Aptamer Designer module — main prediction UI.
// Moved from app/page.tsx during the multi-page restructure.
"use client";

import { useState, useEffect, useRef } from "react";
import { Suspense } from "react";

// Define types
interface PredictionScore {
  interaction_probability: number;
}

interface Prediction {
  gene_sequence: string;
  structure: string;
  score: PredictionScore;
  mfe: number;
  variant_part?: string;
}

interface ResultData {
  query: string;
  predictions: Prediction[];
  error?: string;
  status?: string;
  progress?: number;
  prefix?: string;
  suffix?: string;
  variant_length?: number;
  total_length?: number;
  message?: string;
}

interface ProgressData {
  progress: number;
  status: string;
  remaining_time: number | null;
}

interface JobResponse {
  job_id: string;
  result_url: string;
}

// Updated interface for the form data
interface PredictionFormData {
  amino_acid_sequence: string;
  variant_length: number;
  total_length: number;
  prefix?: string;
  suffix?: string;
}

// Use NEXT_PUBLIC_API_URL or default to your VM
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

// Constants for validation
const DEFAULT_VARIANT_LENGTH = 10;
const DEFAULT_TOTAL_LENGTH = 30;
const MAX_TOTAL_LENGTH = 50;
const MAX_VARIANT_LENGTH = 16; // Added this constant for clarity

// DNA source sequences
const PREFIX_SOURCE = "ATAACTGGTCTTGTTACAGGTCTG";
const SUFFIX_SOURCE = "TCCTTACGTATAATACTACCGAAC";

// Declare window types
declare global {
  interface Window {
    d3: any;
    FornaContainer: any;
    fornac: {
      FornaContainer: any;
    };
  }
}

// Fallback visualization component
function FallbackStructureVisualization({ structure, gene }: { structure: string, gene: string }) {
  return (
    <div className="font-mono text-sm p-3 bg-gray-100 rounded overflow-auto">
      <div className="mb-1">
        <strong>Sequence:</strong>{" "}
        <span className="break-all">{gene}</span>
      </div>
      <div>
        <strong>Structure:</strong>{" "}
        <span className="break-all">{structure}</span>
      </div>
    </div>
  );
}

// RNA structure visualization component
function RNAForna({ 
  gene, 
  structure, 
  id, 
  scriptsLoaded 
}: { 
  gene: string, 
  structure: string, 
  id: string, 
  scriptsLoaded: boolean 
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [initialized, setInitialized] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [initAttempts, setInitAttempts] = useState<number>(0);

  // Reset initialization when inputs change significantly
  useEffect(() => {
    setInitialized(false);
    setError(null);
    // Small delay before attempting visualization
    const timer = setTimeout(() => {
      setInitAttempts(prev => prev + 1);
    }, 500);
    return () => clearTimeout(timer);
  }, [gene, structure, id]);

  useEffect(() => {
    if (!scriptsLoaded || initialized || !containerRef.current || initAttempts === 0) return;
    
    console.log(`Initializing RNA structure for #${id}, attempt ${initAttempts}`);

    // Clear any previous containers with this ID
    const existingContainer = document.querySelector(`#${id} > svg`);
    if (existingContainer) {
      existingContainer.remove();
    }

    const timer = setTimeout(() => {
      try {
        if (typeof window === 'undefined') return;
        
        if (!window.d3) {
          console.error("D3 not found");
          setError("D3 visualization library not loaded yet");
          return;
        }

        const FornaContainer =
          window.FornaContainer ||
          (window.fornac && window.fornac.FornaContainer);
        if (!FornaContainer) {
          console.error("FornaContainer not found", { 
            fornac: window.fornac, 
            standalone: window.FornaContainer 
          });
          
          // If we've tried a few times and still can't find the library, give up
          if (initAttempts > 3) {
            setError("RNA visualization library not properly loaded after multiple attempts");
          } else {
            // Try again with a longer delay
            setTimeout(() => {
              setInitAttempts(prev => prev + 1);
            }, 1000);
          }
          return;
        }

        // Clean strings and ensure they're valid
        const cleanedGene = gene.trim();
        const cleanedStructure = structure.trim();

        if (!cleanedGene || !cleanedStructure) {
          setError("Invalid sequence or structure data");
          return;
        }

        console.log(`Adding RNA to #${id}`, {
          gene: cleanedGene,
          structure: cleanedStructure,
        });

        try {
          // Create a fresh container
          const container = new FornaContainer(`#${id}`);
          
          // Add the RNA with sequence
          container.addRNA(cleanedStructure, { sequence: cleanedGene });
          
          console.log(`Successfully rendered RNA for #${id}`);
          setInitialized(true);
        } catch (renderError) {
          console.error("Error rendering RNA:", renderError);
          
          // If we've tried a few times and still can't render, show the error
          if (initAttempts > 3) {
            setError(`Error rendering: ${renderError instanceof Error ? renderError.message : "Unknown error"}`);
          } else {
            // Try again with a delay
            setTimeout(() => {
              setInitAttempts(prev => prev + 1);
            }, 1000);
          }
        }
      } catch (err) {
        console.error("Error initializing RNA visualization:", err);
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    }, 500); // Shorter initial delay, we'll retry if needed

    return () => clearTimeout(timer);
  }, [scriptsLoaded, gene, structure, id, initialized, initAttempts]);

  if (error) {
    return (
      <div>
        <p className="text-red-500 mb-2">
          Visualization error: {error}
        </p>
        <FallbackStructureVisualization
          structure={structure}
          gene={gene}
        />
      </div>
    );
  }

  return (
    <div className="mt-3">
      <div className="mb-2 p-2 bg-gray-50 border border-gray-300 rounded font-mono text-sm">
        <strong>Sequence:</strong> <span className="break-all">{gene}</span>
      </div>
      <div
        id={id}
        ref={containerRef}
        style={{
          border: "1px solid #ddd",
          borderRadius: "4px",
          minHeight: "250px", // Increased height
          width: "100%",
          overflow: "hidden" // Prevent overflow issues
        }}
        className="rna-structure-container"
      >
        {!initialized && (
          <p className="text-center p-4">
            Loading RNA structure visualization...
            {initAttempts > 1 && ` (attempt ${initAttempts})`}
          </p>
        )}
      </div>
    </div>
  );
}

export default function Home() {
  // Original state variables
  const [sequence, setSequence] = useState<string>("");
  const [variantLength, setVariantLength] = useState<number>(DEFAULT_VARIANT_LENGTH);
  const [variantLengthInput, setVariantLengthInput] = useState<string>(DEFAULT_VARIANT_LENGTH.toString());
  const [totalLength, setTotalLength] = useState<number>(DEFAULT_TOTAL_LENGTH);
  // New state variable for input control
  const [totalLengthInput, setTotalLengthInput] = useState<string>(totalLength.toString());
  
  const [jobId, setJobId] = useState<string>("");
  const [result, setResult] = useState<ResultData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [status, setStatus] = useState<string>("");
  const [remainingTime, setRemainingTime] = useState<number | null>(null);
  const [scriptsLoaded, setScriptsLoaded] = useState<boolean>(false);
  const [resultUrl, setResultUrl] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [lengthError, setLengthError] = useState<string>("");
  const [previewInfo, setPreviewInfo] = useState<{prefix: string, suffix: string} | null>(null);
  
  // State variables for custom sequences
  const [customPrefix, setCustomPrefix] = useState<string>("");
  const [customSuffix, setCustomSuffix] = useState<string>("");
  const [useCustomSequences, setUseCustomSequences] = useState<boolean>(false);
  const [sequenceError, setSequenceError] = useState<string>("");
  
  // State for kill operation
  const [isKilling, setIsKilling] = useState<boolean>(false);
  
  // State variables for time warning
  const [timeWarningShown, setTimeWarningShown] = useState<boolean>(false);
  const [initialEstimate, setInitialEstimate] = useState<number | null>(null);
  const [improvedEstimate, setImprovedEstimate] = useState<number | null>(null);
  const [timeEstimateLoaded, setTimeEstimateLoaded] = useState<boolean>(false);

  // Sync input values with actual values when they change
  useEffect(() => {
    setTotalLengthInput(totalLength.toString());
  }, [totalLength]);
  
  useEffect(() => {
    setVariantLengthInput(variantLength.toString());
  }, [variantLength]);

  // Function to check and handle excessive time estimates - now dynamic
  const checkTimeEstimate = (remainingTime: number | null, progress: number) => {
    if (remainingTime === null) return;
    
    // Mark that we've received a time estimate
    if (!timeEstimateLoaded) {
      setTimeEstimateLoaded(true);
    }
    
    // Record the initial estimate (around 1-2%) for later comparison
    if (progress > 0.5 && progress < 2.5 && initialEstimate === null) {
      setInitialEstimate(remainingTime);
    }
    
    // At 10% progress, record the improved estimate for comparison
    if (progress >= 10 && progress <= 11 && improvedEstimate === null) {
      setImprovedEstimate(remainingTime);
    }
    
    // Dynamically show/hide warning based on current estimate
    if (remainingTime > 600000) {
      setTimeWarningShown(true);
    } else {
      setTimeWarningShown(false);
    }
  };

  // Improved script loading
  useEffect(() => {
    // Function to check if libraries are initialized
    const checkLibraries = () => {
      if (typeof window !== 'undefined' && 
          window.d3 && 
          (window.FornaContainer || (window.fornac && window.fornac.FornaContainer))) {
        console.log("Libraries initialized correctly");
        setScriptsLoaded(true);
        return true;
      }
      return false;
    };
    
    // If already loaded, we're done
    if (scriptsLoaded) return;
    
    // Check immediately in case scripts are already loaded
    if (checkLibraries()) return;
    
    // Set up a series of checks with exponential backoff
    const checkIntervals = [500, 1000, 2000, 4000];
    
    const intervalIds = checkIntervals.map((delay, index) => {
      return setTimeout(() => {
        if (checkLibraries()) {
          // Clear any remaining intervals
          intervalIds.forEach(id => clearTimeout(id));
        } else if (index === checkIntervals.length - 1) {
          // Last attempt, log error and continue anyway
          console.error("Failed to confirm visualization libraries loaded", {
            d3: window?.d3,
            FornaContainer: window?.FornaContainer,
            fornac: window?.fornac
          });
          // Set as loaded anyway so we can try to render
          setScriptsLoaded(true);
        }
      }, delay);
    });
    
    return () => intervalIds.forEach(id => clearTimeout(id));
  }, [scriptsLoaded]);

  // Helper function to calculate GC content
  const calculateGCContent = (sequence: string): number => {
    if (!sequence || sequence.length === 0) return 0;
    const gcCount = (sequence.match(/[GC]/gi) || []).length;
    return (gcCount / sequence.length) * 100;
  };
  
  // Helper function to check for consecutive bases
  const hasConsecutiveRepeats = (sequence: string, maxRepeats: number): boolean => {
    for (let i = 0; i <= sequence.length - maxRepeats - 1; i++) {
      const char = sequence[i];
      let isRepeat = true;
      for (let j = 1; j <= maxRepeats; j++) {
        if (sequence[i + j] !== char) {
          isRepeat = false;
          break;
        }
      }
      if (isRepeat) return true;
    }
    return false;
  };
  
  // Helper function to check for consecutive G or C
  const hasConsecutiveGC = (sequence: string, maxRepeats: number): boolean => {
    let gcStreak = 0;
    for (let i = 0; i < sequence.length; i++) {
      if (sequence[i] === 'G' || sequence[i] === 'C') {
        gcStreak++;
        if (gcStreak > maxRepeats) return true;
      } else {
        gcStreak = 0;
      }
    }
    return false;
  };
  
  // Calculate GC content for entire sequence (prefix + variant + suffix)
  const calculateFullSequenceGCContent = (): { gcContent: number, isValid: boolean } => {
    if (!useCustomSequences || !customPrefix || !customSuffix) return { gcContent: 0, isValid: true };
    
    // For variant region, we need to estimate worst/best cases since it's variable
    const prefixGC = (customPrefix.match(/[GC]/gi) || []).length;
    const suffixGC = (customSuffix.match(/[GC]/gi) || []).length;
    
    // Calculate min/max possible GC in variant region (assuming 0% to 100% GC)
    const minTotalGC = prefixGC + suffixGC;
    const maxTotalGC = prefixGC + suffixGC + variantLength;
    
    const totalLength = customPrefix.length + variantLength + customSuffix.length;
    
    // Min/max overall GC percentages
    const minGCPercent = (minTotalGC / totalLength) * 100;
    const maxGCPercent = (maxTotalGC / totalLength) * 100;
    
    // Average GC content (assuming 50% GC in variable region)
    const avgGCPercent = ((prefixGC + suffixGC + (variantLength * 0.5)) / totalLength) * 100;
    
    return {
      gcContent: avgGCPercent,
      isValid: !(maxGCPercent < 47 || minGCPercent > 55)
    };
  };

  // Add DNA sequence validation function
  const validateDnaSequence = (seq: string): boolean => {
    return /^[ATGCatgc]*$/.test(seq);
  };

  // Handle toggle for custom sequences
  const handleSequenceToggle = (isCustom: boolean) => {
    setUseCustomSequences(isCustom);
    
    if (!isCustom) {
      // When switching back to default mode, restore the default total length
      const newLength = Math.max(variantLength + 2, DEFAULT_TOTAL_LENGTH);
      setTotalLength(newLength);
      setTotalLengthInput(newLength.toString());
    }
  };

  // Handle variant length change with improved input handling
  const handleVariantLengthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Allow any input, including empty string
    setVariantLengthInput(e.target.value);
    
    // Only update the actual value if it's a valid number
    if (e.target.value !== "") {
      const newValue = parseInt(e.target.value);
      if (!isNaN(newValue)) {
        // Show warning if value is too high
        if (newValue > MAX_VARIANT_LENGTH) {
          setLengthError(`Variant length must be between 1 and ${MAX_VARIANT_LENGTH}`);
        } else {
          setLengthError("");
        }
        
        const newVariantLength = Math.max(1, Math.min(MAX_VARIANT_LENGTH, newValue)); // Clamp between 1 and 16
        setVariantLength(newVariantLength);
        
        // Update total length if needed to maintain minimum constraint
        if (totalLength < newVariantLength + 2) {
          const newTotalLength = newVariantLength + 2;
          setTotalLength(newTotalLength);
          setTotalLengthInput(newTotalLength.toString());
        }
      }
    }
  };

  // Validation function for lengths
  const validateLengths = () => {
    if (useCustomSequences) {
      // When using custom sequences, we don't need to validate total length
      // as it's calculated automatically
      return true;
    }
    
    // Get the current value from the input field
    const currentTotalLength = parseInt(totalLengthInput);
    
    // Check if the input is even a valid number
    if (isNaN(currentTotalLength)) {
      setLengthError("Total length must be a valid number");
      return false;
    }
    
    if (currentTotalLength > MAX_TOTAL_LENGTH) {
      setLengthError(`Total length cannot exceed ${MAX_TOTAL_LENGTH}`);
      return false;
    }
    
    if (currentTotalLength < variantLength + 2) {
      setLengthError(`Total length must be at least ${variantLength + 2} (variant length + 2)`);
      return false;
    }
    
    setLengthError("");
    return true;
  };

  // Validate custom sequences
  const validateCustomSequences = (): boolean => {
    // Skip validation if not using custom sequences
    if (!useCustomSequences) return true;
    
    // Check if sequences contain only A, T, G, C
    if (customPrefix && !validateDnaSequence(customPrefix)) {
      setSequenceError("Prefix must contain only A, T, G, C bases");
      return false;
    }
    
    if (customSuffix && !validateDnaSequence(customSuffix)) {
      setSequenceError("Suffix must contain only A, T, G, C bases");
      return false;
    }
    
    // If using custom sequences, both must be provided
    if ((!customPrefix || customPrefix.trim() === "") || 
        (!customSuffix || customSuffix.trim() === "")) {
      setSequenceError("Both prefix and suffix must be provided when using custom sequences");
      return false;
    }
    
    // Check if the custom sequences + variant length exceed the total length limit
    const combinedLength = customPrefix.length + customSuffix.length + variantLength;
    if (combinedLength > MAX_TOTAL_LENGTH) {
      setSequenceError(`Combined length (prefix + variant + suffix = ${combinedLength}) exceeds maximum of ${MAX_TOTAL_LENGTH}`);
      return false;
    }
    
    // Check for consecutive repeats
    if (hasConsecutiveRepeats(customPrefix, 4)) {
      setSequenceError("Prefix contains more than 4 consecutive identical bases");
      return false;
    }
    
    if (hasConsecutiveRepeats(customSuffix, 4)) {
      setSequenceError("Suffix contains more than 4 consecutive identical bases");
      return false;
    }
    
    // Check for consecutive G/C repeats
    // if (hasConsecutiveGC(customPrefix, 4)) {
    //   setSequenceError("Prefix contains more than 4 consecutive G or C bases");
    //   return false;
    // }
    
    // if (hasConsecutiveGC(customSuffix, 4)) {
    //   setSequenceError("Suffix contains more than 4 consecutive G or C bases");
    //   return false;
    // }
    
    // Check if GC content can possibly be in the valid range
    const { isValid } = calculateFullSequenceGCContent();
    if (!isValid) {
      setSequenceError("Your prefix and suffix combination cannot achieve 47-55% GC content with any variable region");
      return false;
    }
    
    setSequenceError("");
    return true;
  };

  // Update preview info when settings change
  useEffect(() => {
    if (!validateLengths()) {
      setPreviewInfo(null);
      return;
    }
    
    if (useCustomSequences) {
      // When using custom sequences, show them in the preview
      if (customPrefix && customSuffix && validateCustomSequences()) {
        setPreviewInfo({ 
          prefix: customPrefix.toUpperCase(), 
          suffix: customSuffix.toUpperCase() 
        });
      } else {
        setPreviewInfo(null);
      }
    } else {
      // Only calculate if we have a valid totalLength
      const parsedTotalLength = parseInt(totalLengthInput);
      if (isNaN(parsedTotalLength) || parsedTotalLength < variantLength + 2) {
        setPreviewInfo(null);
        return;
      }
      
      // Use default calculation for auto-generated sequences
      const remainingLength = totalLength - variantLength;
      let prefixLength, suffixLength;
      
      if (remainingLength % 2 === 0) {
        prefixLength = suffixLength = remainingLength / 2;
      } else {
        prefixLength = Math.floor(remainingLength / 2) + 1;
        suffixLength = Math.floor(remainingLength / 2);
      }
      
      // Extract prefix and suffix from source strings
      const prefix = PREFIX_SOURCE.substring(0, prefixLength);
      const suffix = SUFFIX_SOURCE.substring(0, suffixLength);
      
      setPreviewInfo({ prefix, suffix });
    }
  }, [variantLength, totalLength, totalLengthInput, useCustomSequences, customPrefix, customSuffix]);

  // On mount, check URL for existing job
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    // Check for jobId in URL
    const searchParams = new URLSearchParams(window.location.search);
    let initialJobId = searchParams.get('jobId');
    
    // If not in search params, check for results path format
    if (!initialJobId) {
      const match = window.location.pathname.match(/\/results\/([a-zA-Z0-9-]+)/);
      if (match?.[1]) {
        initialJobId = match[1];
      }
    }
    
    if (initialJobId) {
      fetchResult(initialJobId);
    }
  }, []);

  useEffect(() => {
    // Apply custom styling to reduce font size of nucleotide labels
    const style = document.createElement('style');
    style.textContent = `
      .rna-structure-container text {
        font-size: 14px !important;
        font-family: monospace !important;
      }
      .rna-structure-container .nucleotide {
        font-size: 8px !important;
      }
    `;
    document.head.appendChild(style);
    
    return () => {
      document.head.removeChild(style);
    };
  }, []);
  
  // Load D3 & Forna scripts
  const handleFornaScriptLoad = () => {
    console.log("Forna script loaded, waiting for libraries to initialize");
    
    // Check if libraries are ready immediately
    if (typeof window !== 'undefined' && 
        window.d3 && 
        (window.FornaContainer || (window.fornac && window.fornac.FornaContainer))) {
      console.log("Libraries initialized on first check");
      setScriptsLoaded(true);
      return;
    }
    
    // First retry after 1 second
    setTimeout(() => {
      if (typeof window !== 'undefined' && 
          window.d3 && 
          (window.FornaContainer || (window.fornac && window.fornac.FornaContainer))) {
        console.log("Libraries initialized after 1s");
        setScriptsLoaded(true);
        return;
      }
      
      // Second retry after 3 seconds
      setTimeout(() => {
        if (typeof window !== 'undefined' && 
            window.d3 && 
            (window.FornaContainer || (window.fornac && window.fornac.FornaContainer))) {
          console.log("Libraries initialized after 3s");
          setScriptsLoaded(true);
        } else {
          console.error("Failed to initialize visualization libraries", {
            d3: window.d3,
            FornaContainer: window.FornaContainer,
            fornac: window.fornac
          });
        }
      }, 2000);
    }, 1000);
  };

  const fetchResult = async (id: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/results/${id}`);
      if (!res.ok) {
        setErrorMessage(
          res.status === 404
            ? "Results not found."
            : `Error: ${res.statusText}`
        );
        setLoading(false);
        return;
      }
      const data = await res.json() as ResultData;
      if (data.status && data.status !== "Completed" && data.status !== "Terminated") {
        setStatus(data.status);
        setProgress(data.progress || 0);
        setJobId(id);
      } else {
        setResult(data);
        setLoading(false);
      }
    } catch (error) {
      setErrorMessage("An error occurred while retrieving results.");
      setLoading(false);
    }
  };

  // Update the killJob function to properly handle partial results
  const killJob = async () => {
    if (!jobId) return;
    
    setIsKilling(true);
    
    try {
      const res = await fetch(`${API_BASE}/kill/${jobId}`, {
        method: "POST",
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      console.log("Kill response data:", data); // Add logging to see the response structure
      
      // If we have partial results in the response
      if (data.result && (data.result.predictions || Array.isArray(data.result.predictions))) {
        console.log("Setting partial results:", data.result);
        setResult(data.result);
        setLoading(false);
        setJobId("");
      } else {
        // If no results yet, fetch the latest results from the server
        try {
          console.log("No results in kill response, fetching from results endpoint");
          const resultsRes = await fetch(`${API_BASE}/results/${jobId}`);
          if (resultsRes.ok) {
            const resultsData = await resultsRes.json();
            console.log("Fetched results data:", resultsData);
            
            if (resultsData.predictions || Array.isArray(resultsData.predictions)) {
              setResult(resultsData);
            } else {
              throw new Error("No usable results found");
            }
          } else {
            throw new Error(`Error fetching results: ${resultsRes.statusText}`);
          }
        } catch (fetchErr) {
          console.error("Error fetching results after kill:", fetchErr);
          setErrorMessage("Job terminated. No partial results available.");
        }
        
        setLoading(false);
        setJobId("");
      }
    } catch (err) {
      console.error("Error in kill job:", err);
      setErrorMessage(err instanceof Error ? err.message : "Error occurred while terminating job.");
      setLoading(false);
      setJobId("");
    } finally {
      setIsKilling(false);
    }
  };

  // Poll for progress if a job is running
  useEffect(() => {
    if (!jobId) return;
    
    const iv = setInterval(async () => {
      try {
        const res = await fetch(
          `${API_BASE}/progress?job_id=${jobId}`
        );
        if (!res.ok) return;
        
        const p = await res.json() as ProgressData;
        setProgress(p.progress);
        setStatus(p.status || "Processing");
        setRemainingTime(p.remaining_time);
        
        // Check time estimate after updating state
        checkTimeEstimate(p.remaining_time, p.progress);

        if (p.status === "Completed" || p.status === "Terminated" || p.progress === 100) {
          const r = await fetch(`${API_BASE}/results/${jobId}`);
          const d = await r.json() as ResultData;
          if (d.predictions || d.error) {
            setResult(d);
            setJobId("");
            setLoading(false);
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 1000);
    return () => clearInterval(iv);
  }, [jobId]);

  // Reset every form + job field to submit a fresh query.
  // Wired to the "Start New Task" button that appears in the results panel.
  const handleStartNewTask = () => {
    setSequence("");
    setVariantLength(DEFAULT_VARIANT_LENGTH);
    setVariantLengthInput(DEFAULT_VARIANT_LENGTH.toString());
    setTotalLength(DEFAULT_TOTAL_LENGTH);
    setTotalLengthInput(DEFAULT_TOTAL_LENGTH.toString());
    setCustomPrefix("");
    setCustomSuffix("");
    setUseCustomSequences(false);
    setJobId("");
    setResult(null);
    setLoading(false);
    setProgress(0);
    setStatus("");
    setRemainingTime(null);
    setResultUrl("");
    setErrorMessage("");
    setLengthError("");
    setSequenceError("");
    setPreviewInfo(null);
    setIsKilling(false);
    setTimeWarningShown(false);
    setInitialEstimate(null);
    setImprovedEstimate(null);
    setTimeEstimateLoaded(false);

    // On submit we pushState'd to `/results/<jobId>` (see handleSubmit).
    // Reset the URL back to /predict so the address bar reflects a fresh form,
    // and drop any lingering query params.
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", "/predict");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate both lengths and custom sequences before submitting
    if (!validateLengths() || !validateCustomSequences()) {
      return;
    }

    setLoading(true);
    setProgress(0);
    setRemainingTime(null);
    setResult(null);
    setErrorMessage("");
    setResultUrl("");
    
    // Reset time warning states
    setTimeWarningShown(false);
    setInitialEstimate(null);
    setImprovedEstimate(null);
    setTimeEstimateLoaded(false);

    try {
      const body: PredictionFormData = {
        amino_acid_sequence: sequence,
        variant_length: variantLength,
        total_length: totalLength
      };
      
      // Set total_length based on the mode
      if (useCustomSequences) {
        // When using custom sequences, calculate the actual total length
        const calculatedTotalLength = customPrefix.length + variantLength + customSuffix.length;
        
        // Include calculated total length
        body.total_length = calculatedTotalLength;
        body.prefix = customPrefix.toUpperCase();
        body.suffix = customSuffix.toUpperCase();
      } else {
        // Use the value from the input field for default mode
        body.total_length = totalLength;
      }
      
      const res = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server: ${res.status} ${res.statusText}`);
      }

      const d = await res.json() as JobResponse;
      setJobId(d.job_id);
      setResultUrl(d.result_url);
      
      if (typeof window !== 'undefined') {
        window.history.pushState({}, "", `/results/${d.job_id}`);
      }
    } catch (err) {
      console.error(err);
      setErrorMessage(err instanceof Error ? err.message : "Error occurred while fetching.");
      setLoading(false);
    }
  };

  const formatTime = (s: number) =>
    isNaN(s)
      ? "N/A"
      : `${Math.floor(s / 60)}:${String(
          Math.floor(s % 60)
        ).padStart(2, "0")}`;

  return (
    <main className="min-h-screen flex items-center justify-center p-4" 
          style={{
            backgroundColor: "rgb(245, 240, 255)", // Custom light purple background
            backgroundImage: "url('/images/background.png')", 
            backgroundSize: "cover", 
            backgroundPosition: "center", 
            backgroundBlendMode: "overlay"
          }}>
      {/* D3 + Fornac scripts now live in app/predict/layout.tsx.
          The polling useEffect in this component picks them up when ready. */}

      <div className="w-full max-w-xl bg-white rounded-lg shadow-lg p-6 relative">
        {/* Decorative header with DNA-like image */}
        <div className="absolute top-0 left-0 w-full h-16 rounded-t-lg overflow-hidden" style={{ backgroundColor: "rgb(110, 40, 150)" }}>
          <div className="absolute inset-0 opacity-30" style={{
            backgroundImage: "url('/api/placeholder/800/100')",
            backgroundSize: "cover",
            backgroundPosition: "center",
            backgroundRepeat: "no-repeat"
          }}></div>
          <div className="flex items-center justify-center h-full">
            <img 
              src="/images/icon_trans.png" 
              alt="DNA helix logo" 
              className="h-15 w-15 rounded-full bg-white p-1 mr-3"
            />
            <div>
              <h1 className="text-2xl font-bold text-white">
                APIPred Web 1.0
              </h1>
            </div>
          </div>
        </div>
        
        {/* Main content with padding to account for the header */}
        <div className="mt-16 pt-4">
          <p className="text-sm mb-6" style={{ color: "rgb(110, 40, 150)" }}>
            Prediction of putative aptamer sequences for protein target
          </p>

          {errorMessage && (
            <div className="bg-red-100 border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              <strong>Error:</strong> {errorMessage}
            </div>
          )}

          {resultUrl && (
            <div className="px-4 py-3 rounded mb-4" style={{ backgroundColor: "rgb(230, 220, 250)", borderColor: "rgb(180, 140, 230)", color: "rgb(80, 30, 110)" }}>
              <p>
                <strong>Bookmark this page</strong> to access your results later (valid for 90 days).
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col">
            <input
              type="text"
              placeholder="Enter amino acid sequence"
              value={sequence}
              onChange={(e) => setSequence(e.target.value)}
              className="border-purple-300 rounded-md p-2 mb-4 focus:ring-2 focus:ring-purple-500"
              required
            />
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: "rgb(90, 30, 120)" }}>
                  Variant Length
                </label>
                <input
                  type="number"
                  value={variantLengthInput}
                  onChange={handleVariantLengthChange}
                  onBlur={() => {
                    // Validate and apply constraints when the field loses focus
                    const newValue = parseInt(variantLengthInput);
                    if (isNaN(newValue) || newValue < 1) {
                      // If invalid, reset to minimum valid value
                      setVariantLength(1);
                      setVariantLengthInput("1");
                    } else if (newValue > MAX_VARIANT_LENGTH) {
                      // If too large, cap at maximum
                      setVariantLength(MAX_VARIANT_LENGTH);
                      setVariantLengthInput(MAX_VARIANT_LENGTH.toString());
                    } else {
                      // Valid value, ensure it's set
                      setVariantLength(newValue);
                      setVariantLengthInput(newValue.toString());
                    }
                  }}
                  min="1"
                  max={MAX_VARIANT_LENGTH.toString()}
                  className="w-full rounded-md p-2"
                  style={{ borderColor: "rgb(180, 140, 230)", outlineColor: "rgb(130, 50, 170)" }}
                />
                <p className="text-xs text-purple-500 mt-1">
                  Length of variable region (1-{MAX_VARIANT_LENGTH})
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-purple-700 mb-1" style={{ color: "rgb(90, 30, 120)" }}>
                  Total Length
                </label>
                <input
                  type="number"
                  value={totalLengthInput}
                  onChange={(e) => {
                    // Allow any input, including empty string
                    setTotalLengthInput(e.target.value);
                    
                    // Only update the actual value if it's a valid number
                    if (e.target.value !== "") {
                      const newValue = parseInt(e.target.value);
                      if (!isNaN(newValue)) {
                        setTotalLength(newValue);
                      }
                    }
                  }}
                  onBlur={() => {
                    // Validate and apply constraints when the field loses focus
                    const newValue = parseInt(totalLengthInput);
                    if (isNaN(newValue) || newValue < variantLength + 2) {
                      // If invalid, reset to minimum valid value
                      setTotalLength(variantLength + 2);
                      setTotalLengthInput((variantLength + 2).toString());
                    } else if (newValue > MAX_TOTAL_LENGTH) {
                      // If too large, cap at maximum
                      setTotalLength(MAX_TOTAL_LENGTH);
                      setTotalLengthInput(MAX_TOTAL_LENGTH.toString());
                    } else {
                      // Valid value, ensure it's set
                      setTotalLength(newValue);
                      setTotalLengthInput(newValue.toString());
                    }
                  }}
                  min={variantLength + 2}
                  max={MAX_TOTAL_LENGTH}
                  className="w-full border-purple-300 rounded-md p-2 focus:ring-2 focus:ring-purple-500"
                  disabled={useCustomSequences} // Disable when using custom sequences
                />
                <p className="text-xs text-purple-500 mt-1">
                  {useCustomSequences 
                    ? `Total length: ${customPrefix.length + variantLength + customSuffix.length} bases (calculated automatically)` 
                    : `Total sequence length (${variantLength + 2}-${MAX_TOTAL_LENGTH})`}
                </p>
              </div>
            </div>
            
            {/* Add toggle for custom sequences */}
            <div className="mb-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={useCustomSequences}
                  onChange={(e) => handleSequenceToggle(e.target.checked)}
                  className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-purple-300 rounded"
                />
                <span className="ml-2 text-sm text-purple-700">
                  Use custom prefix and suffix sequences
                </span>
              </label>
            </div>
            
            {/* Show custom sequence inputs when toggled */}
            {useCustomSequences && (
              <>
                <div className="bg-purple-50 border-purple-200 p-3 rounded mb-4">
                  <h3 className="text-sm font-medium text-purple-800 mb-1">DNA Sequence Design Guidelines</h3>
                  <ul className="text-xs text-purple-700 list-disc pl-5 space-y-1">
                    <li>No more than 4 consecutive identical bases (e.g., AAAAA)</li>
                    {/* <li>No more than 4 consecutive G or C bases in a row (e.g., GGCGG)</li> */}
                    <li>GC content should be between 47-55% of the total sequence</li>
                  </ul>
                  
                  {/* Add GC content analysis */}
                  {customPrefix && customSuffix && (
                    <div className="mt-2 pt-2 border-t border-purple-200">
                      <h4 className="text-xs font-medium text-purple-800 mb-1">Sequence Analysis:</h4>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="font-medium">Prefix GC:</span> {calculateGCContent(customPrefix).toFixed(1)}%
                        </div>
                        <div>
                          <span className="font-medium">Suffix GC:</span> {calculateGCContent(customSuffix).toFixed(1)}%
                        </div>
                      </div>
                      
                      {/* Overall GC content estimate */}
                      {(() => {
                        const { gcContent, isValid } = calculateFullSequenceGCContent();
                        const colorClass = isValid ? "text-green-600" : "text-red-600";
                        return (
                          <div className="mt-1">
                            <span className="text-xs font-medium">Expected Overall GC:</span>{" "}
                            <span className={`text-xs font-medium ${colorClass}`}>
                              {gcContent.toFixed(1)}% {!isValid && "(Warning: May not meet 47-55% requirement)"}
                            </span>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-purple-700 mb-1">
                      Custom Prefix
                    </label>
                    <input
                      type="text"
                      value={customPrefix}
                      onChange={(e) => setCustomPrefix(e.target.value.toUpperCase())}
                      placeholder="e.g., ATAACTGGTCTTGT"
                      className="w-full border-purple-300 rounded-md p-2 focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-purple-700 mb-1">
                      Custom Suffix
                    </label>
                    <input
                      type="text"
                      value={customSuffix}
                      onChange={(e) => setCustomSuffix(e.target.value.toUpperCase())}
                      placeholder="e.g., TCCTTACGTATAAT"
                      className="w-full border-purple-300 rounded-md p-2 focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>
              </>
            )}
            
            {/* Display validation errors */}
            {(lengthError || sequenceError) && (
              <div className="bg-red-100 border-red-400 text-red-700 px-4 py-2 rounded mb-4 text-sm">
                {lengthError || sequenceError}
              </div>
            )}
            
            {/* Sequence preview */}
            {previewInfo && (
              <div className="bg-gray-50 p-3 rounded border border-purple-200 mb-4">
                <h3 className="font-medium text-purple-700 mb-2">Sequence Preview</h3>
                <div className="font-mono text-sm break-all">
                  <span className="text-indigo-600">{previewInfo.prefix}</span>
                  <span className="text-red-600">{"N".repeat(Math.min(10, variantLength))}{variantLength > 10 ? "..." : ""}</span>
                  <span className="text-purple-600">{previewInfo.suffix}</span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Your sequence will have a {useCustomSequences ? "custom" : "fixed"} prefix ({previewInfo.prefix.length} bases), 
                  a variable region ({variantLength} bases), 
                  and a {useCustomSequences ? "custom" : "fixed"} suffix ({previewInfo.suffix.length} bases).
                  {useCustomSequences && ` Total length: ${previewInfo.prefix.length + variantLength + previewInfo.suffix.length} bases.`}
                </p>
                
                {/* Add sequence quality indicators for custom sequences */}
                {useCustomSequences && customPrefix && customSuffix && (
                  <div className="mt-3 pt-2 border-t border-gray-200">
                    <h4 className="text-xs font-medium text-purple-700 mb-1">Sequence Quality Check:</h4>
                    <ul className="text-xs space-y-1">
                      <li className="flex items-center">
                        <span className={hasConsecutiveRepeats(customPrefix, 4) || hasConsecutiveRepeats(customSuffix, 4) ? "text-red-500" : "text-green-500"}>
                          {hasConsecutiveRepeats(customPrefix, 4) || hasConsecutiveRepeats(customSuffix, 4) ? "✗" : "✓"}
                        </span>
                        <span className="ml-2">No more than 4 consecutive identical bases</span>
                      </li>
                      <li className="flex items-center">
                        {/* <span className={hasConsecutiveGC(customPrefix, 4) || hasConsecutiveGC(customSuffix, 4) ? "text-red-500" : "text-green-500"}>
                          {hasConsecutiveGC(customPrefix, 4) || hasConsecutiveGC(customSuffix, 4) ? "✗" : "✓"}
                        </span>
                        <span className="ml-2">No more than 4 consecutive G/C bases</span> */}
                      </li>
                      <li className="flex items-center">
                        {(() => {
                          const { isValid } = calculateFullSequenceGCContent();
                          return (
                            <>
                              <span className={isValid ? "text-green-500" : "text-red-500"}>
                                {isValid ? "✓" : "✗"}
                              </span>
                              <span className="ml-2">GC content between 47-55%</span>
                            </>
                          );
                        })()}
                      </li>
                    </ul>
                  </div>
                )}
              </div>
            )}
            
            <button
              type="submit"
              className="font-semibold py-2 rounded-md"
              style={{
                backgroundColor: "rgb(120, 40, 160)",
                color: "white",
                transition: "background-color 0.2s ease",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "rgb(100, 30, 140)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "rgb(120, 40, 160)"; }}
              disabled={loading || !!lengthError || !!sequenceError}
            >
              {loading ? "Processing..." : "Predict"}
            </button>
          </form>

          {loading && (
            <div className="mt-4 text-center">
              <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                <div
                  className="h-2.5 rounded-full"
                  style={{ backgroundColor: "rgb(130, 50, 170)", width: `${progress}%` }}
                />
              </div>
              <p className="text-gray-600">
                {status || "Processing"}... {progress.toFixed(2)}%
              </p>
              
              {/* Time estimate display - with warm reminder when loading */}
              {remainingTime !== null ? (
                <p className="text-gray-600">
                  Estimated remaining time: {formatTime(remainingTime)}
                </p>
              ) : (
                /* Warm reminder when time estimate is loading */
                <p className="text-gray-600 italic">
                  Calculating estimated time... this may take a moment
                </p>
              )}
              
              {/* Add time estimate warning - now dynamic */}
              {timeWarningShown && (
                <div className="my-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-800">
                  <p className="font-medium mb-1">⚠️ Long estimated processing time detected</p>
                  <p>The current estimate exceeds one week (10,000+ minutes). Please note:</p>
                  <ul className="list-disc pl-5 mt-1 text-xs space-y-1">
                    <li>Initial time estimates are typically much longer than actual processing time</li>
                    <li>Estimates usually shrink significantly as processing continues</li>
                    <li>You can use the "Stop Process & Show Results" button to get partial results at any time</li>
                  </ul>
                  {improvedEstimate !== null && initialEstimate !== null && (
                    <p className="mt-2 text-xs font-medium">
                      Your initial estimate was {formatTime(initialEstimate)} and has already improved to {formatTime(improvedEstimate)} (a {Math.round((1 - improvedEstimate/initialEstimate) * 100)}% reduction)
                    </p>
                  )}
                </div>
              )}
              
              {/* Kill button */}
              <button
                onClick={killJob}
                disabled={isKilling}
                className="mt-3 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isKilling ? "Stopping..." : "Stop Process & Show Results"}
              </button>
              <p className="text-xs text-gray-500 mt-1">
                This will terminate the job and show any results found so far.
              </p>
            </div>
          )}

          {result && !loading && (
            <div className="mt-6 break-words">
              {/* Reset the form and clear the job to submit a new query */}
              <div className="mb-4 flex justify-end">
                <button
                  type="button"
                  onClick={handleStartNewTask}
                  className="px-4 py-2 rounded-md text-sm font-medium text-white"
                  style={{ backgroundColor: "rgb(120, 40, 160)" }}
                >
                  Start New Task
                </button>
              </div>

              {/* Show terminated job message if applicable */}
              {result.status === "Terminated" && (
                <div className="bg-yellow-100 border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
                  <p className="font-bold">Process Terminated</p>
                  <p>{result.message || "The job was stopped before completion. Showing partial results."}</p>
                </div>
              )}
              
              {result.error ? (
                <p className="text-red-500 text-center">
                  {result.error}
                </p>
              ) : (
                <>
                  <h2 className="text-xl font-semibold mb-2 text-purple-800">
                    Prediction Results for: {result.query}
                  </h2>
                  
                  {result.prefix && result.suffix && (
                    <div className="bg-purple-50 p-3 rounded border border-purple-200 mb-4">
                      <h3 className="font-medium text-purple-700 mb-1">Sequence Configuration</h3>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p><strong>Variant Length:</strong> {result.variant_length}</p>
                          <p><strong>Total Length:</strong> {result.total_length}</p>
                        </div>
                        <div>
                          <p><strong>Prefix:</strong> <span className="font-mono">{result.prefix}</span></p>
                          <p><strong>Suffix:</strong> <span className="font-mono">{result.suffix}</span></p>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {result.predictions && result.predictions.length > 0 ? (
                    <>
                      {/* ADD THIS EXPLANATION SECTION */}
                      <div className="bg-blue-50 border border-blue-200 p-4 rounded-md mb-4">
                        <h3 className="font-medium text-blue-800 mb-2">📊 Results Explanation</h3>
                        <div className="text-sm text-blue-700 space-y-1">
                          <p>• <strong>Ranking:</strong> Results are ranked by descending order of log score (highest to lowest)</p>
                          <p>• <strong>Log Score:</strong> The natural logarithm of the interaction probability is used to better show differences between results</p>
                          <p>• <strong>Why Log?</strong> High ranking interaction probabilities are often close to one (e.g., 0.99989), so taking the log transforms them to more readable values (e.g., -0.0000478)</p>
                          <p>• <strong>Higher is Better:</strong> Less negative log scores indicate higher interaction probabilities</p>
                        </div>
                      </div>
                      
                      <ul className="space-y-6">
                        {result.predictions.map((item, idx) => (
                          <li
                            key={idx}
                            className="p-4 border border-purple-200 rounded shadow-sm bg-white"
                          >
                            <div className="mb-3">
                              <p className="text-lg font-medium text-purple-700">
                                Result #{idx + 1}
                              </p>
                              <p>
                                <strong>Log Score:</strong>{" "}
                                {typeof item.score.interaction_probability === 'number' 
                                  ? Math.log(item.score.interaction_probability).toFixed(10)
                                  : 'N/A'}
                              </p>
                              <p>
                                <strong>MFE:</strong> {typeof item.mfe === 'number' ? item.mfe.toFixed(2) : item.mfe}
                              </p>
                              {item.variant_part && (
                                <p>
                                  <strong>Variable Region:</strong>{" "}
                                  <span className="font-mono">{item.variant_part}</span>
                                </p>
                              )}
                            </div>
                            <div className="mt-4">
                              <p className="font-semibold mb-1 text-purple-700">
                                DNA Structure:
                              </p>
                              <Suspense fallback={
                                <FallbackStructureVisualization 
                                  structure={item.structure} 
                                  gene={item.gene_sequence} 
                                />
                              }>
                                <RNAForna
                                  gene={item.gene_sequence}
                                  structure={item.structure}
                                  id={`rna-structure-${idx}-${result.status || 'normal'}`} // Add status to make IDs unique on rerenders
                                  scriptsLoaded={scriptsLoaded}
                                />
                              </Suspense>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <p className="text-center text-gray-700">
                      No predictions available yet. This could be because the process was terminated very early.
                    </p>
                  )}
                </>
              )}
            </div>
          )}
          
          {/* Add decorative footer image */}
          <div className="mt-6 pt-4 border-t text-center" style={{ borderColor: "rgb(200, 180, 240)" }}>
            <img 
              src="/images/pa_interaction.png" 
              alt="DNA structure" 
              className="mx-auto h-80 w-80 opacity-60"
            />
            <img 
              src="/images/bottom.png" 
              alt="DNA structure" 
              className="mx-auto h-40 w-80 opacity-60"
            />
            <p className="text-xs mt-2" style={{ color: "rgb(130, 60, 180)" }}>APIPred Web 1.0 © 2025</p>
          </div>
        </div>
      </div>
    </main>
  );
}
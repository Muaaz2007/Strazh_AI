"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Upload, CheckCircle, FileText, Keyboard, ChevronLeft, ChevronRight, Check, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { SlideButton } from "@/components/ui/slide-button";

let pdfjsLib: any = null;

// Initialize PDF.js on client side only
async function initializePDFjs() {
    if (pdfjsLib) return pdfjsLib;

    try {
        pdfjsLib = await import("pdfjs-dist");
        pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;
        return pdfjsLib;
    } catch (error) {
        console.error("Failed to load PDF.js:", error);
        return null;
    }
}

// Helper function to parse structured labels from PDF text
function parseStructuredLabels(text: string): Record<string, string> {
    const patterns: Record<string, RegExp> = {
        name: /System\s+Name\s*:?\s*([^\n]+)/i,
        domain: /Domain\s*:?\s*([^\n]+)/i,
        description: /Description\s*:?\s*([^\n]+)/i,
        intended_users: /Intended\s+Users\s*:?\s*([^\n]+)/i,
        deployment: /Deployment\s*:?\s*([^\n]+)/i,
        data_types: /Data\s+Types?\s*:?\s*([^\n]+)/i,
        outputs: /Outputs?\s*:?\s*([^\n]+)/i,
    };

    const extracted: Record<string, string> = {};

    for (const [field, pattern] of Object.entries(patterns)) {
        const match = text.match(pattern);
        extracted[field] = match ? match[1].trim() : "";
    }

    return extracted;
}

// Function to validate extracted fields
function validateExtractedFields(fields: Record<string, string>): {
    valid: boolean;
    missingFields: string[];
} {
    const requiredFields = ["name", "domain", "description", "intended_users", "deployment", "data_types", "outputs"];
    const missing = requiredFields.filter(field => !fields[field] || fields[field].trim() === "");

    return {
        valid: missing.length === 0,
        missingFields: missing
    };
}

// Function to extract text from PDF
async function extractTextFromPDF(file: File): Promise<string> {
    const pdf = await initializePDFjs();

    if (!pdf) {
        throw new Error("PDF.js not available");
    }

    const arrayBuffer = await file.arrayBuffer();
    const pdfdoc = await pdf.getDocument({ data: arrayBuffer }).promise;
    let fullText = "";

    for (let i = 1; i <= pdfdoc.numPages; i++) {
        const page = await pdfdoc.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map((item: any) => item.str).join(" ");
        fullText += pageText + "\n";
    }

    return fullText;
}

const steps = [
    { id: "basic", title: "Basic Info" },
    { id: "context", title: "Deployment" },
    { id: "data", title: "Capabilities" },
];

const aiFacts = [
    {
        title: "Why AI Compliance Matters",
        fact: "AI systems can inadvertently perpetuate biases from training data. Regular audits help identify and correct these biases."
    },
    {
        title: "EU AI Act Impact",
        fact: "The EU AI Act requires high-risk AI systems to undergo rigorous conformity assessments before deployment."
    },
    {
        title: "Security is Critical",
        fact: "Adversarial attacks can manipulate AI systems. Strazh AI helps identify and mitigate these vulnerabilities."
    },
    {
        title: "Data Privacy Protection",
        fact: "GDPR compliance is essential. AI systems must handle personal data responsibly and securely."
    },
    {
        title: "Transparent Decision-Making",
        fact: "Users have the right to understand how AI systems make decisions affecting them. Explainability is key."
    },
];

const contentVariants = {
    hidden: { opacity: 0, x: 50 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.3 } },
    exit: { opacity: 0, x: -50, transition: { duration: 0.2 } },
};

const fadeInUp = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export default function InputFormPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [loadingProgress, setLoadingProgress] = useState(0);
    const [currentFactIndex, setCurrentFactIndex] = useState(0);
    const [mode, setMode] = useState<'select' | 'upload' | 'manual'>('select');
    const [uploading, setUploading] = useState(false);
    const [uploadSuccess, setUploadSuccess] = useState(false);
    const [uploadError, setUploadError] = useState(false);
    const [missingFields, setMissingFields] = useState<string[]>([]);

    // Multi-step state
    const [currentStep, setCurrentStep] = useState(0);

    const [form, setForm] = useState({
        name: "",
        domain: "",
        description: "",
        intended_users: "",
        outputs: "",
        deployment: "",
        data_types: "",
    });

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            setUploading(true);
            setUploadSuccess(false);
            setUploadError(false);
            setMissingFields([]);

            try {
                // Extract text from PDF
                const pdfText = await extractTextFromPDF(file);

                // Parse structured labels
                const extractedFields = parseStructuredLabels(pdfText);

                // Validate extracted fields
                const validation = validateExtractedFields(extractedFields);

                if (validation.valid) {
                    // All fields found - populate form and show success
                    setForm(prev => ({
                        ...prev,
                        ...extractedFields
                    }));

                    setTimeout(() => {
                        setUploading(false);
                        setUploadSuccess(true);
                        setCurrentStep(0);
                        setMode('manual');
                        setTimeout(() => setUploadSuccess(false), 8000);
                    }, 500);
                } else {
                    // Missing fields - show error
                    setUploading(false);
                    setUploadError(true);
                    setMissingFields(validation.missingFields);
                }
            } catch (error) {
                console.error("PDF extraction error:", error);
                setUploading(false);
                setUploadError(true);
                setMissingFields(["name", "domain", "description", "intended_users", "deployment", "data_types", "outputs"]);
            }
        }
    };

    const nextStep = () => {
        if (currentStep < steps.length - 1) setCurrentStep(prev => prev + 1);
    };

    const prevStep = () => {
        if (currentStep > 0) setCurrentStep(prev => prev - 1);
    };

    const isStepValid = () => {
        if (currentStep === 0) return form.name.trim() !== "" && form.domain.trim() !== "" && form.description.trim() !== "";
        if (currentStep === 1) return form.intended_users.trim() !== "" && form.deployment.trim() !== "";
        if (currentStep === 2) return form.outputs.trim() !== "" && form.data_types.trim() !== "";
        return true;
    };

    const handleSubmit = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!isStepValid()) return;

        setLoading(true);
        setLoadingProgress(0);

        // Smooth progress updates
        const progressInterval = setInterval(() => {
            setLoadingProgress(prev => {
                if (prev < 90) return prev + Math.random() * 30;
                return prev;
            });
        }, 300);

        // Cycle through facts while loading
        const factInterval = setInterval(() => {
            setCurrentFactIndex(prev => (prev + 1) % aiFacts.length);
        }, 1500);

        try {
            // TODO: Replace with your real backend API call
            // Example structure for connecting to your AI backend:
            const payload = {
                system_info: {
                    name: form.name,
                    domain: form.domain,
                    description: form.description,
                },
                deployment_context: {
                    intended_users: form.intended_users,
                    deployment: form.deployment,
                },
                capabilities: {
                    data_types: form.data_types,
                    outputs: form.outputs,
                },
            };

            // Simulate API call - replace with actual endpoint
            // const response = await fetch('/api/compliance-analysis', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify(payload)
            // });
            // const reportData = await response.json();

            // For now, simulate the call
            await new Promise(resolve => setTimeout(resolve, 2000));

            setLoadingProgress(100);

            setTimeout(() => {
                clearInterval(progressInterval);
                clearInterval(factInterval);
                // TODO: Pass report data to the report page
                // You can use router state or query params to pass data
                router.push("/report");
            }, 500);
        } catch (error) {
            console.error("Submission error:", error);
            clearInterval(progressInterval);
            clearInterval(factInterval);
            setLoading(false);
            setLoadingProgress(0);
            // TODO: Show error message to user
        }
    };

    if (loading) {
        return (
            <div className="loading-screen">
                <motion.div
                    key={currentFactIndex}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.3 }}
                    className="text-center max-w-2xl"
                >
                    <div className="loading-spinner mb-6" />
                    <h2 className="text-2xl font-bold text-[#3B2314] mb-4">
                        {aiFacts[currentFactIndex].title}
                    </h2>
                    <p className="text-lg text-[#8B6F5E] leading-relaxed mb-8">
                        {aiFacts[currentFactIndex].fact}
                    </p>

                    {/* Progress Bar */}
                    <div className="mb-6">
                        <div className="w-full bg-[#E8D5C4] rounded-full h-2 overflow-hidden mb-2">
                            <motion.div
                                className="h-full bg-[#A0522D]"
                                initial={{ width: 0 }}
                                animate={{ width: `${loadingProgress}%` }}
                                transition={{ duration: 0.3, ease: "easeOut" }}
                            />
                        </div>
                        <motion.p
                            className="text-sm font-semibold text-[#A0522D]"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                        >
                            {Math.round(loadingProgress)}% Complete
                        </motion.p>
                    </div>

                    <p className="text-sm text-[#8B6F5E] font-medium">
                        Analyzing your AI system against EU AI Act, NIST, and OWASP standards...
                    </p>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen w-full py-12 flex items-center justify-start flex-col pt-24">
            <div className="w-full max-w-3xl mx-auto flex flex-col px-6">
                <div className="section-header mb-12">
                    <h1>Describe Your AI System</h1>
                </div>

                {mode === 'select' ? (
                    <>
                        <Link href="/" className="back-link mb-8">
                            ← Back to Home
                        </Link>

                        {/* Selection Mode */}
                        <div className="w-full flex justify-center">
                            <div className="grid md:grid-cols-2 gap-8 max-w-5xl w-full">
                            <button
                                onClick={() => setMode('upload')}
                                className="flex flex-col text-left p-10 border-2 border-transparent bg-white hover:border-[#A0522D] rounded-2xl shadow-sm transition-all hover:shadow-md group"
                            >
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="p-4 bg-[#F5EDE4] rounded-xl group-hover:bg-[#A0522D] transition-colors">
                                        <Upload className="w-8 h-8 text-[#A0522D] group-hover:text-white transition-colors" />
                                    </div>
                                    <h2 className="text-3xl font-bold text-[#3B2314]">Upload PDF</h2>
                                </div>
                                <p className="text-xl text-[#8B6F5E] leading-relaxed">
                                    Upload a document with all information. We will automatically extract the required fields using OCR.
                                </p>
                            </button>

                            <button
                                onClick={() => {
                                    setCurrentStep(0);
                                    setMode('manual');
                                }}
                                className="flex flex-col text-left p-10 border-2 border-transparent bg-white hover:border-[#A0522D] rounded-2xl shadow-sm transition-all hover:shadow-md group"
                            >
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="p-4 bg-[#F5EDE4] rounded-xl group-hover:bg-[#A0522D] transition-colors">
                                        <Keyboard className="w-8 h-8 text-[#A0522D] group-hover:text-white transition-colors" />
                                    </div>
                                    <h2 className="text-3xl font-bold text-[#3B2314]">Enter Manually</h2>
                                </div>
                                <p className="text-xl text-[#8B6F5E] leading-relaxed">
                                    Fill out a guided form about your AI system's purpose, deployment, and data usage.
                                </p>
                            </button>
                        </div>
                        </div>
                    </>
                ) : (
                    <>
                        <button onClick={() => setMode('select')} className="back-link bg-transparent border-none cursor-pointer flex items-center p-0 font-inherit font-medium mb-8">
                            ← Back to Selection
                        </button>

                        {mode === 'upload' && (
                            <div className="w-full flex justify-center">
                                <div className="max-w-2xl w-full">
                                <label className="text-center p-8 border-2 border-dashed border-[#E8D5C4] rounded-lg cursor-pointer bg-white hover:bg-[#F5F5DC] transition-colors flex flex-col items-center justify-center gap-4 shadow-sm">
                                    <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
                                    {uploading ? (
                                        <>
                                            <div className="loading-spinner" style={{ width: 32, height: 32, margin: 0, borderWidth: 3 }} />
                                            <span className="text-[#A0522D] font-medium text-lg">Extracting data via OCR...</span>
                                        </>
                                    ) : (
                                        <>
                                            <div className="flex gap-4 mb-2">
                                                <FileText className="w-8 h-8 text-[#A0522D]" />
                                                <Upload className="w-8 h-8 text-[#A0522D]" />
                                            </div>
                                            <div className="text-[#3B2314] font-medium text-lg">Upload system documentation (PDF)</div>
                                            <div className="text-sm text-[#8B6F5E]">We will extract the required details automatically using OCR.</div>
                                        </>
                                    )}
                                </label>
                            </div>
                            </div>
                        )}

                        {mode === 'manual' && (
                            <div className="w-full">
                                {uploadSuccess && (
                                    <div className="mb-6 p-4 bg-[#F5EDE4] border border-[#A0522D]/30 rounded-lg flex items-center gap-3 shadow-sm">
                                        <CheckCircle className="w-6 h-6 text-[#A0522D] flex-shrink-0" />
                                        <span className="text-[#3B2314] font-medium">Information extracted successfully! Please review and modify if needed.</span>
                                    </div>
                                )}

                                {uploadError && (
                                    <div className="mb-6 p-4 bg-[#FFE8E8] border border-[#E35336] rounded-lg shadow-sm">
                                        <div className="flex items-start gap-3">
                                            <AlertCircle className="w-6 h-6 text-[#E35336] flex-shrink-0 mt-0.5" />
                                            <div className="flex-1">
                                                <span className="text-[#3B2314] font-medium block">Could not extract required information from PDF</span>
                                                <span className="text-[#8B6F5E] text-sm block mt-2">Missing fields:</span>
                                                <ul className="text-[#8B6F5E] text-sm mt-1 ml-4 space-y-1">
                                                    {missingFields.map(field => (
                                                        <li key={field} className="capitalize">• {field.replace(/_/g, ' ')}</li>
                                                    ))}
                                                </ul>
                                                <span className="text-[#8B6F5E] text-sm block mt-3">Please ensure your PDF contains all required information with clear labels (e.g., "System Name:", "Domain:", etc.)</span>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Progress indicator */}
                                <motion.div className="mb-8 mt-8" initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
                                    <div className="flex justify-between mb-2">
                                        {steps.map((step, index) => (
                                            <motion.div key={index} className="flex flex-col items-center" whileHover={{ scale: 1.05 }}>
                                                <motion.div
                                                    className={cn(
                                                        "w-4 h-4 rounded-full cursor-pointer transition-colors duration-300",
                                                        index < currentStep ? "bg-[#A0522D]" : index === currentStep ? "bg-[#A0522D] ring-4 ring-[#A0522D]/20" : "bg-[#E8D5C4]"
                                                    )}
                                                    onClick={() => { if (index <= currentStep) setCurrentStep(index); }}
                                                    whileTap={{ scale: 0.95 }}
                                                />
                                                <motion.span className={cn("text-xs mt-2 hidden md:block", index === currentStep ? "text-[#A0522D] font-bold" : "text-[#8B6F5E]")}>
                                                    {step.title}
                                                </motion.span>
                                            </motion.div>
                                        ))}
                                    </div>
                                    <div className="w-full bg-[#E8D5C4] h-1.5 rounded-full overflow-hidden mt-2">
                                        <motion.div
                                            className="h-full bg-[#A0522D]"
                                            initial={{ width: 0 }}
                                            animate={{ width: `${(currentStep / (steps.length - 1)) * 100}%` }}
                                            transition={{ duration: 0.3 }}
                                        />
                                    </div>
                                </motion.div>

                                {/* Form Content */}
                                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}>
                                    <form onSubmit={handleSubmit} className="relative">
                                        <AnimatePresence mode="wait">
                                            <motion.div key={currentStep} initial="hidden" animate="visible" exit="exit" variants={contentVariants}>

                                                {/* Step 1: Basic Info */}
                                                {currentStep === 0 && (
                                                    <div className="space-y-6">
                                                        <div style={{ marginBottom: '1.5rem' }}>
                                                            <h2 className="text-xl font-bold text-[#3B2314] mb-1">Basic Profile</h2>
                                                            <p className="text-sm text-[#8B6F5E]">Identify your AI system and its primary domain.</p>
                                                        </div>

                                                        <motion.div variants={fadeInUp} className="form-group">
                                                            <label htmlFor="name">System Name <span className="text-[#E35336]">*</span></label>
                                                            <input id="name" type="text" className="form-input" placeholder='e.g. "HireEmotionAI"' value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoFocus required />
                                                        </motion.div>

                                                        <motion.div variants={fadeInUp} className="form-group">
                                                            <label htmlFor="domain">Domain / Sector <span className="text-[#E35336]">*</span></label>
                                                            <input id="domain" type="text" className="form-input" placeholder='e.g. "employment"' value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} required />
                                                        </motion.div>

                                                        <motion.div variants={fadeInUp} className="form-group">
                                                            <label htmlFor="description">System Description <span className="text-[#E35336]">*</span></label>
                                                            <textarea id="description" className="form-input" style={{ minHeight: "100px", resize: "vertical" }} placeholder='e.g. "AI system to score job applicants..."' value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
                                                        </motion.div>
                                                    </div>
                                                )}

                                                {/* Step 2: Context */}
                                                {currentStep === 1 && (
                                                    <div className="space-y-6">
                                                        <div style={{ marginBottom: '1.5rem' }}>
                                                            <h2 className="text-xl font-bold text-[#3B2314] mb-1">Deployment Context</h2>
                                                            <p className="text-sm text-[#8B6F5E]">Define the users and target environment for your AI.</p>
                                                        </div>

                                                        <motion.div variants={fadeInUp} className="form-group">
                                                            <label htmlFor="intended_users">Intended Users <span className="text-[#E35336]">*</span></label>
                                                            <input id="intended_users" type="text" className="form-input" placeholder='e.g. "HR departments"' value={form.intended_users} onChange={(e) => setForm({ ...form, intended_users: e.target.value })} autoFocus required />
                                                        </motion.div>

                                                        <motion.div variants={fadeInUp} className="form-group">
                                                            <label htmlFor="deployment">Deployment Region &amp; Context <span className="text-[#E35336]">*</span></label>
                                                            <input id="deployment" type="text" className="form-input" placeholder='e.g. "Enterprise HR, EU"' value={form.deployment} onChange={(e) => setForm({ ...form, deployment: e.target.value })} required />
                                                        </motion.div>
                                                    </div>
                                                )}

                                                {/* Step 3: Data & Outputs */}
                                                {currentStep === 2 && (
                                                    <div className="space-y-6">
                                                        <div style={{ marginBottom: '1.5rem' }}>
                                                            <h2 className="text-xl font-bold text-[#3B2314] mb-1">Capabilities &amp; Data</h2>
                                                            <p className="text-sm text-[#8B6F5E]">Detail the data inputs processed and the final system outputs.</p>
                                                        </div>

                                                        <motion.div variants={fadeInUp} className="form-group">
                                                            <label htmlFor="data_types">Data Types Used <span className="text-[#E35336]">*</span></label>
                                                            <input id="data_types" type="text" className="form-input" placeholder='e.g. "Biometric, facial expressions..."' value={form.data_types} onChange={(e) => setForm({ ...form, data_types: e.target.value })} autoFocus required />
                                                        </motion.div>

                                                        <motion.div variants={fadeInUp} className="form-group">
                                                            <label htmlFor="outputs">System Outputs <span className="text-[#E35336]">*</span></label>
                                                            <input id="outputs" type="text" className="form-input" placeholder='e.g. "Emotional stability score, hiring recommendation"' value={form.outputs} onChange={(e) => setForm({ ...form, outputs: e.target.value })} required />
                                                        </motion.div>
                                                    </div>
                                                )}
                                            </motion.div>
                                        </AnimatePresence>

                                        <div className="flex justify-between mt-8 pt-6 border-t border-[#E8D5C4]">
                                            <button
                                                type="button"
                                                onClick={() => currentStep > 0 && setCurrentStep(currentStep - 1)}
                                                className="hero__btn-secondary"
                                                style={{ width: 'auto' }}
                                            >
                                                ← Back
                                            </button>
                                            {currentStep < steps.length - 1 ? (
                                                <button
                                                    type="button"
                                                    onClick={() => setCurrentStep(currentStep + 1)}
                                                    className="hero__btn-primary"
                                                    style={{ width: 'auto' }}
                                                >
                                                    Next →
                                                </button>
                                            ) : (
                                                <SlideButton
                                                    onSuccess={handleSubmit}
                                                    
                                                ></SlideButton>
                                            )}
                                        </div>
                                    </form>
                                </motion.div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}

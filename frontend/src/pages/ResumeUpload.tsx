import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Upload, Loader2, CheckCircle, AlertCircle, Sparkles, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { ResumeModal } from "@/components/ResumeModal";
import { Toaster, toast } from "../components/Toaster";

interface ResumeData {
  name?: string;
  email?: string;
  phone?: string;
  skills?: string[];
  experience?: Array<{ title: string; company: string; duration: string }>;
  education?: string;
  certifications?: string[];
  achievements?: string[];
  rawText?: string;
}

export function ResumeUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [resumeData, setResumeData] = useState<ResumeData | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile?.type === "application/pdf") {
      setFile(droppedFile);
      setError(null);
      setResumeData(null);
      setShowModal(false);
    } else {
      setError("Please upload a PDF file");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
      setResumeData(null);
      setShowModal(false);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      const id = crypto.randomUUID();
      formData.append("user_id", id);
      formData.append("query", "Analyze this resume");
      formData.append("file", file);
      localStorage.setItem("user_id", id);

      const response = await fetch(`${process.env.BUN_PUBLIC_BACKEND_ENDPOINT}/v1/graph/upload_resume`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullContent += chunk;
      }

      // Parse SSE format: extract everything after "data: " that isn't [DOC]
      const lines = fullContent.split("\n");
      let cleanContent = "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("data: ")) {
          const data = trimmed.slice(6);
          if (!data.startsWith("[DOC]")) {
            cleanContent += data + "\n";
          }
        }
      }

      try {
        const cleaned = cleanContent.replace(/^```json\n?/, "").replace(/\n?```$/, "").trim();
        const parsed = JSON.parse(cleaned);
        setResumeData(parsed);
      } catch {
        // Try to parse Python Answer object format
        const answerStart = cleanContent.indexOf("Answer(");
        if (answerStart !== -1) {
          // Find the end by counting parentheses
          const startParen = cleanContent.indexOf("(", answerStart);
          let parenCount = 1;
          let endIdx = startParen + 1;
          while (endIdx < cleanContent.length && parenCount > 0) {
            if (cleanContent[endIdx] === "(") parenCount++;
            else if (cleanContent[endIdx] === ")") parenCount--;
            endIdx++;
          }
          const answerStr = cleanContent.slice(startParen + 1, endIdx - 1);
          const parsed: ResumeData = {};

          // Extract name
          const nameMatch = answerStr.match(/name='([^']*)'/);
          if (nameMatch?.[1]) {
            parsed.name = nameMatch[1];
          }

          // Extract skills list
          const skillsMatch = answerStr.match(/skills=\[(.*?)\]/s);
          if (skillsMatch && skillsMatch[1]?.trim()) {
            parsed.skills = skillsMatch[1].split(",").map(s => s.trim().replace(/^'|'$/g, "")).filter(s => s);
          }

          // Extract education
          const eduMatch = answerStr.match(/education='([^']*)'/);
          if (eduMatch?.[1]) parsed.education = eduMatch[1];

          // Extract work_experience (empty list or populated)
          const expMatch = answerStr.match(/work_experience=\[(.*?)\]/s);
          if (expMatch) {
            const expContent = expMatch[1]?.trim() ?? "";
            if (expContent) {
              parsed.experience = expContent.split("},").map(e => {
                const titleMatch = e.match(/title='([^']*)'/);
                const companyMatch = e.match(/company='([^']*)'/);
                const durationMatch = e.match(/duration='([^']*)'/);
                return {
                  title: titleMatch?.[1] ?? '',
                  company: companyMatch?.[1] ?? '',
                  duration: durationMatch?.[1] ?? ''
                };
              });
            } else {
              parsed.experience = [];
            }
          }

          // Extract certifications
          const certMatch = answerStr.match(/certifications=\[(.*?)\]/s);
          if (certMatch?.[1]?.trim()) {
            parsed.certifications = certMatch[1].split(",").map(s => s.trim().replace(/^'|'$/g, "")).filter(s => s);
          }

          // Extract achievements
          const achMatch = answerStr.match(/achievements=\[(.*?)\]/s);
          if (achMatch?.[1]?.trim()) {
            parsed.achievements = achMatch[1].split("', '").map(s => s.trim().replace(/^'|'$/g, "")).filter(s => s);
          }

          setResumeData(parsed);
          setShowModal(true);

          // Check if the response indicates an invalid resume
          const cleanedForCheck = cleanContent.trim();
          if (cleanedForCheck.includes("Please upload a valid resume")) {
            toast("Please provide a valid resume. The uploaded document does not appear to be a resume.", "error");
            setShowModal(false);
            return;
          }
        } else {
          // Fallback to raw text if parsing fails
          const rawText = cleanContent.trim();
          setResumeData({ rawText: rawText });

          // Check if the raw text indicates an invalid resume
          if (rawText.includes("Please upload a valid resume")) {
            toast("Please provide a valid resume. The uploaded document does not appear to be a resume.", "error");
            setShowModal(false);
            return;
          }

          setShowModal(true);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 -left-32 w-96 h-96 bg-gradient-to-br from-violet-500/20 to-transparent rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-gradient-to-br from-indigo-500/20 to-transparent rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-4 py-12 space-y-10">
        {/* Hero Section */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 rounded-full text-sm font-medium">
            <Sparkles className="h-4 w-4" />
            AI-Powered Resume Analysis
          </div>
          <h1 className="text-5xl font-bold bg-gradient-to-r from-slate-900 via-indigo-800 to-violet-700 dark:from-white dark:via-indigo-200 dark:to-violet-300 bg-clip-text text-transparent">
            Upload Your Resume
          </h1>
          <p className="text-lg text-slate-600 dark:text-slate-400 max-w-xl mx-auto">
            Paste your resume and let our AI extract and organize your information instantly
          </p>
        </div>

        {/* Upload Card */}
        <Card className="border-0 shadow-2xl shadow-slate-200/50 dark:shadow-slate-900/50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl overflow-hidden">
          <CardContent className="p-8">
            {/* Drop Zone */}
            <div
              className={`relative rounded-2xl border-2 border-dashed transition-all duration-300 ${
                isDragging
                  ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950/50 scale-[1.02]"
                  : "border-slate-200 dark:border-slate-700 hover:border-indigo-400 dark:hover:border-indigo-600"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileSelect}
              />

              {file ? (
                <div className="py-12 flex flex-col items-center gap-4">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30">
                    <CheckCircle className="h-10 w-10 text-white" />
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-semibold text-slate-900 dark:text-white">{file.name}</p>
                    <p className="text-sm text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                      setResumeData(null);
                      setShowModal(false);
                    }}
                    className="text-sm text-slate-500 hover:text-red-500 transition-colors"
                  >
                    Remove file
                  </button>
                </div>
              ) : (
                <div className="py-16 flex flex-col items-center gap-4">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                    <Upload className="h-10 w-10 text-white" />
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-medium text-slate-700 dark:text-slate-200">
                      Drop your resume here or <span className="text-indigo-600 dark:text-indigo-400">browse</span>
                    </p>
                    <p className="text-sm text-slate-500 mt-1">PDF files up to 10MB</p>
                  </div>
                </div>
              )}
            </div>

            {/* Upload Button */}
            <Button
              onClick={handleUpload}
              disabled={!file || isUploading}
              className="w-full h-12 mt-6 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-lg shadow-indigo-500/30 transition-all duration-300"
              size="lg"
            >
              {isUploading ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing with AI...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  Extract Resume Data
                </span>
              )}
            </Button>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-3 text-red-600 bg-red-50 dark:bg-red-900/20 p-4 rounded-xl mt-4">
                <AlertCircle className="h-5 w-5 shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Chat Link */}
        <div className="text-center pt-4">
          <Link to="/chat">
            <Button
              variant="outline"
              size="lg"
              className="px-8 h-12 border-2 hover:bg-gradient-to-r hover:from-indigo-600 hover:to-violet-600 hover:text-white hover:border-transparent transition-all duration-300"
            >
              Start Chatting
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Resume Modal */}
      <ResumeModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        data={resumeData || {}}
      />

      {/* Toast Notifications */}
      <Toaster />
    </div>
  );
}
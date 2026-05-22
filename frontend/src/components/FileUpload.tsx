import { useState, useRef, type DragEvent } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Upload, FileText, Loader2 } from "lucide-react";

interface FileUploadProps {
  onUpload: (file: File, query: string) => void;
  isUploading: boolean;
}

export function FileUpload({ onUpload, isUploading }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [query, setQuery] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === "application/pdf") {
      setFile(droppedFile);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleUpload = () => {
    if (file && query.trim()) {
      onUpload(file, query);
    }
  };

  return (
    <div className="flex flex-col items-center space-y-6 max-w-2xl mx-auto">
      <div className="text-center space-y-2">
        <div className="text-5xl">📄</div>
        <h2 className="text-2xl font-semibold">Upload Your Resume</h2>
        <p className="text-muted-foreground">
          Upload a PDF resume and ask questions about it
        </p>
      </div>

      <div
        className={`w-full border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          isDragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/30 hover:border-primary"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileSelect}
        />

        {file ? (
          <div className="flex items-center justify-center gap-3">
            <FileText className="h-8 w-8 text-primary" />
            <span className="font-medium">{file.name}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFile(null)}
            >
              Remove
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex justify-center">
              <Upload className="h-12 w-12 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-primary hover:underline cursor-pointer">
                Click to browse files
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={handleFileSelect}
                />
              </label>
              <p className="text-xs text-muted-foreground">
                PDF files only, max 10MB
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="w-full space-y-3">
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What would you like to know about this resume?"
          className="min-h-[80px]"
        />
        <Button
          className="w-full"
          size="lg"
          onClick={handleUpload}
          disabled={!file || !query.trim() || isUploading}
        >
          {isUploading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4 mr-2" />
              Upload & Analyze
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
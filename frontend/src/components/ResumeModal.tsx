import { X, User, Mail, Phone, Briefcase, GraduationCap, Sparkles } from "lucide-react";

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

interface ResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: ResumeData;
}

export function ResumeModal({ isOpen, onClose, data }: ResumeModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-white dark:bg-slate-900 rounded-3xl shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-900/95 backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">Resume Analysis</h2>
              <p className="text-sm text-slate-500">AI-extracted information</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            <X className="h-5 w-5 text-slate-600 dark:text-slate-300" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Basic Info */}
          {(data.name || data.email || data.phone) && (
            <div className="grid gap-4 md:grid-cols-3">
              {data.name && (
                <div className="flex items-start gap-3 p-4 rounded-2xl bg-gradient-to-br from-violet-50 to-indigo-50 dark:from-violet-950/50 dark:to-indigo-950/50">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shrink-0">
                    <User className="h-5 w-5 text-white" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Name</p>
                    <p className="font-semibold text-slate-900 dark:text-white truncate">{data.name}</p>
                  </div>
                </div>
              )}
              {data.email && (
                <div className="flex items-start gap-3 p-4 rounded-2xl bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-950/50 dark:to-cyan-950/50">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center shrink-0">
                    <Mail className="h-5 w-5 text-white" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Email</p>
                    <p className="font-semibold text-slate-900 dark:text-white truncate">{data.email}</p>
                  </div>
                </div>
              )}
              {data.phone && (
                <div className="flex items-start gap-3 p-4 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950/50 dark:to-teal-950/50">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shrink-0">
                    <Phone className="h-5 w-5 text-white" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Phone</p>
                    <p className="font-semibold text-slate-900 dark:text-white truncate">{data.phone}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Skills */}
          {data.skills && data.skills.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                Skills
              </div>
              <div className="flex flex-wrap gap-2">
                {data.skills.map((skill, i) => (
                  <span
                    key={i}
                    className="px-4 py-2 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/50 dark:to-orange-950/50 text-amber-700 dark:text-amber-300 rounded-full text-sm font-medium border border-amber-200 dark:border-amber-800"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Experience */}
          {data.experience && data.experience.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                  <Briefcase className="h-4 w-4 text-white" />
                </div>
                Experience
              </div>
              <div className="space-y-3">
                {data.experience.map((exp, i) => (
                  <div key={i} className="flex items-center justify-between p-4 rounded-2xl bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800/50 dark:to-slate-800">
                    <div className="flex items-center gap-4">
                      <div className="w-3 h-3 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600" />
                      <div>
                        <p className="font-semibold text-slate-900 dark:text-white">{exp.title}</p>
                        <p className="text-sm text-slate-500">{exp.company}</p>
                      </div>
                    </div>
                    <span className="text-sm font-medium text-slate-400 bg-white dark:bg-slate-900 px-3 py-1 rounded-full">{exp.duration}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Education */}
          {data.education && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                  <GraduationCap className="h-4 w-4 text-white" />
                </div>
                Education
              </div>
              <div className="p-4 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950/50 dark:to-teal-950/50">
                <p className="font-medium text-slate-900 dark:text-white whitespace-pre-wrap">{data.education}</p>
              </div>
            </div>
          )}

          {/* Certifications */}
          {data.certifications && data.certifications.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                Certifications
              </div>
              <div className="flex flex-wrap gap-2">
                {data.certifications.map((cert, i) => (
                  <span
                    key={i}
                    className="px-4 py-2 bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-950/50 dark:to-purple-950/50 text-violet-700 dark:text-violet-300 rounded-full text-sm font-medium border border-violet-200 dark:border-violet-800"
                  >
                    {cert}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Achievements */}
          {data.achievements && data.achievements.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                Achievements
              </div>
              <div className="space-y-2">
                {data.achievements.map((ach, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/50 dark:to-orange-950/50">
                    <div className="w-2 h-2 rounded-full bg-amber-500 mt-2 shrink-0" />
                    <p className="text-sm text-slate-700 dark:text-slate-300">{ach}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty state - only show if no structured data AND no raw text */}
          {((!data.name && !data.email && !data.phone && (!data.skills || data.skills.length === 0) && (!data.experience || data.experience.length === 0) && (!data.education || data.education.length === 0)) && !data.rawText) && (
            <div className="text-center py-8 text-slate-500">
              <p>No data could be extracted from this resume.</p>
            </div>
          )}

          {/* Raw Text Display */}
          {data.rawText && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-wider">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-slate-500 to-slate-600 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                Extracted Information
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                {data.rawText}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
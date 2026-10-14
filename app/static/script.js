const { useState, useEffect, useRef } = React;

// Unified fetch wrapper to handle token exhaustion and server error interception
(() => {
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
        try {
            const response = await originalFetch(...args);
            if (response.status === 429) {
                const clone = response.clone();
                try {
                    const data = await clone.json();
                    if (data && (data.status === "exhausted" || data.detail === "exhausted" || (data.detail && data.detail.status === "exhausted"))) {
                        const retryAfter = data.retry_after || (data.detail && data.detail.retry_after) || "15 minutes";
                        window.alert(`Sorry, API tokens exhausted. Please try again after ${retryAfter}.`);
                    }
                } catch (e) {
                    window.alert("Sorry, API tokens exhausted. Please try again later.");
                }
            } else if (!response.ok) {
                const contentType = response.headers.get("content-type");
                if (!contentType || !contentType.includes("application/json")) {
                    const safeJson = { detail: "An unexpected server error occurred. Please try again." };
                    return new Response(JSON.stringify(safeJson), {
                        status: response.status,
                        statusText: response.statusText,
                        headers: { 'Content-Type': 'application/json' }
                    });
                }
            }
            return response;
        } catch (err) {
            const safeJson = { detail: "Connection to server failed. Please check your network connection." };
            return new Response(JSON.stringify(safeJson), {
                status: 503,
                statusText: "Service Unavailable",
                headers: { 'Content-Type': 'application/json' }
            });
        }
    };
})();

/* ==========================================================================
   Lucide Inline SVG Icons
   ========================================================================== */
const PlusIcon = ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
    </svg>
);

const BookmarkIcon = ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
    </svg>
);

const SparklesIcon = ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
    </svg>
);

const UserIcon = ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
);

const CopyIcon = ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
    </svg>
);

const CheckIcon = ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
);

const ShieldIcon = ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
);

const MenuIcon = ({ className = "w-6 h-6" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
    </svg>
);

const ArrowUpIcon = ({ className = "w-4 h-4" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" />
    </svg>
);

const EditIcon = ({ className = "w-3.5 h-3.5" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
    </svg>
);

/* ==========================================================================
   Sidebar Component (Oxford Blue styling, aligned typography specs)
   ========================================================================== */
const Sidebar = ({ activeSession, onSelectSession, onNewSession, isOpen, toggleSidebar, historyList, onSelectHistoryItem }) => {
    return (
        <aside className={`bg-[#001233] border-r border-[#1e3d5f]/20 flex-col justify-between flex-shrink-0 h-full relative overflow-hidden transition-all duration-300 ${isOpen ? 'w-[280px] flex' : 'w-0 hidden'}`}>
            <div className="flex flex-col flex-1 min-h-0 w-[280px]">
                {/* Logo header: Centered and shrunken */}
                <div className="p-4 border-b border-[#1e3d5f]/15 flex items-center justify-center w-full">
                    <div className="max-w-[110px] w-full flex justify-center">
                        <img
                            src="https://www.protiviti.com/themes/custom/protiviti/components/source/images/logo/gl-en.svg"
                            alt="Protiviti"
                            className="max-w-full h-auto object-contain block mx-auto"
                            style={{ filter: 'brightness(0) invert(1)' }}
                            onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = '/static/Protiviti_logo1.webp'; }}
                        />
                    </div>
                </div>

                {/* CTA buttons: New JD and Saved JD stacked */}
                <div className="px-4 py-3 flex flex-col gap-2">
                    <button
                        onClick={() => { onNewSession(); toggleSidebar(); }}
                        className="w-full border border-dashed border-[#5fa8ff]/60 hover:border-[#5fa8ff] text-slate-200 bg-transparent hover:bg-[#023e8a]/20 p-2.5 rounded-lg flex items-center justify-center gap-2 text-xs font-semibold transition-colors"
                    >
                        <PlusIcon className="w-3.5 h-3.5 text-[#5fa8ff]" />
                        <span>New Job Description</span>
                    </button>
                    <button
                        onClick={() => { onSelectSession('session-saved'); toggleSidebar(); }}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold w-full text-left transition-colors truncate ${activeSession === 'session-saved' ? 'bg-[#002855] text-[#5fa8ff] border-l-2 border-[#5fa8ff] pl-[10px]' : 'text-slate-400 hover:bg-[#001845]/40 hover:text-slate-200'}`}
                    >
                        <BookmarkIcon className="w-3.5 h-3.5 text-[#5fa8ff] flex-shrink-0" />
                        <span>Saved JD</span>
                    </button>
                    <button
                        onClick={() => { onSelectSession('session-interviews'); toggleSidebar(); }}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold w-full text-left transition-colors truncate ${activeSession === 'session-interviews' ? 'bg-[#002855] text-[#5fa8ff] border-l-2 border-[#5fa8ff] pl-[10px]' : 'text-slate-400 hover:bg-[#001845]/40 hover:text-slate-200'}`}
                    >
                        <svg className="w-3.5 h-3.5 text-[#5fa8ff] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                        <span>Interview Sessions</span>
                    </button>
                    <button
                        onClick={() => { onSelectSession('session-role-alignment'); toggleSidebar(); }}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold w-full text-left transition-colors truncate ${activeSession === 'session-role-alignment' ? 'bg-[#002855] text-[#5fa8ff] border-l-2 border-[#5fa8ff] pl-[10px]' : 'text-slate-400 hover:bg-[#001845]/40 hover:text-slate-200'}`}
                    >
                        <svg className="w-3.5 h-3.5 text-[#5fa8ff] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 9m0 8V9m0 0L9 7" />
                        </svg>
                        <span>Role Alignment</span>
                    </button>
                    <button
                        onClick={() => { onSelectSession('session-client-feedback'); toggleSidebar(); }}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold w-full text-left transition-colors truncate ${activeSession === 'session-client-feedback' ? 'bg-[#002855] text-[#5fa8ff] border-l-2 border-[#5fa8ff] pl-[10px]' : 'text-slate-400 hover:bg-[#001845]/40 hover:text-slate-200'}`}
                    >
                        <svg className="w-3.5 h-3.5 text-[#5fa8ff] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <span>Client Feedbacks</span>
                    </button>
                    <button
                        onClick={() => { onSelectSession('session-resume-standardizer'); toggleSidebar(); }}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold w-full text-left transition-colors truncate ${activeSession === 'session-resume-standardizer' ? 'bg-[#002855] text-[#5fa8ff] border-l-2 border-[#5fa8ff] pl-[10px]' : 'text-slate-400 hover:bg-[#001845]/40 hover:text-slate-200'}`}
                    >
                        <svg className="w-3.5 h-3.5 text-[#5fa8ff] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span>Resume Standardization Tool</span>
                    </button>
                </div>

                {/* Spacer to push content to the bottom */}
                <div className="flex-1"></div>
            </div>

            {/* Footer branding */}
            <div className="p-4 border-t border-[#1e3d5f]/15 w-[280px]">
                <div className="text-[10px] text-slate-500 font-medium leading-relaxed">© Protiviti | Global Consulting</div>
                <div className="flex items-center gap-1.5 mt-1 text-[9px] text-slate-600 font-bold tracking-wide">
                    <ShieldIcon className="w-3 h-3 text-[#5fa8ff]" />
                    <span>SECURE</span>
                    <span>•</span>
                    <span>INTELLIGENT</span>
                    <span>•</span>
                    <span>ENTERPRISE</span>
                </div>
            </div>
        </aside>
    );
};

const stripQuestionTags = (text) => {
    if (!text) return "";
    let cleaned = text.trim();
    let prev = "";
    while (cleaned !== prev) {
        prev = cleaned;
        cleaned = cleaned.replace(/^\[[^\]]+\]\s*/g, '');
        cleaned = cleaned.replace(/^\([^\)]+\)\s*/g, '');
        cleaned = cleaned.replace(/^:\s*/g, '');
        cleaned = cleaned.trim();
    }
    return cleaned;
};

/* ==========================================================================
   Saved JDs Dashboard Component (vibrant dark-blue grid)
   ========================================================================== */
const SavedJDsDashboard = ({ historyList, onSelectHistoryItem, onNewSession, onDeleteHistoryItem, onShowConfirm }) => {
    const [searchQuery, setSearchQuery] = React.useState("");
    const [sortOrder, setSortOrder] = React.useState("desc");

    const filteredHistory = historyList.filter(item => {
        const titleLower = (item.title || "").toLowerCase();
        const demandsLower = (item.demands || "").toLowerCase();
        return !titleLower.includes("overall_score") &&
            !titleLower.includes("overallscore") &&
            !demandsLower.includes("overall_score") &&
            !demandsLower.includes("overallscore");
    }).filter(item => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return (item.title || "").toLowerCase().includes(q) ||
               (item.demands || "").toLowerCase().includes(q);
    }).sort((a, b) => {
        const dateA = new Date(a.created_at);
        const dateB = new Date(b.created_at);
        return sortOrder === "asc" ? dateA - dateB : dateB - dateA;
    });

    return (
        <div className="flex-1 overflow-y-auto px-6 py-8 w-full animate-fade-in-up">
            <div className="flex flex-wrap items-center justify-end gap-3 mb-6">
                <div className="relative">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Search job descriptions..."
                        className="bg-[#001233] border border-[#002855] text-slate-200 text-xs rounded-lg pl-8 pr-3 py-2 w-56 focus:outline-none focus:border-[#5fa8ff] placeholder-slate-500"
                    />
                    <svg className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                    </svg>
                </div>
                <select
                    value={sortOrder}
                    onChange={e => setSortOrder(e.target.value)}
                    className="bg-[#001233] border border-[#002855] text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-[#5fa8ff] cursor-pointer"
                >
                    <option value="desc">Newest First</option>
                    <option value="asc">Oldest First</option>
                </select>
                <button
                    onClick={onNewSession}
                    className="bg-[#023E8A] hover:bg-[#3a7bd5] text-white text-xs font-bold px-4 py-2.5 rounded-lg shadow-md transition-colors flex items-center gap-2"
                >
                    <PlusIcon className="w-3.5 h-3.5 text-[#5fa8ff] flex-shrink-0" />
                    <span>New Job Description</span>
                </button>
            </div>

            {filteredHistory.length === 0 ? (
                <div className="bg-[#001233] border border-[#002855] rounded-xl p-8 text-center text-slate-400 text-xs">
                    {searchQuery.trim() ? "No job descriptions match your search." : "No job descriptions have been saved yet. Generate one to populate this list."}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredHistory.map(item => (
                        <div
                            key={item.id}
                            className="bg-[#001233] border border-[#002855] hover:border-[#5fa8ff]/30 rounded-xl p-5 flex flex-col justify-between shadow-md transition-all group cursor-pointer"
                            onClick={() => onSelectHistoryItem(item.id)}
                        >
                            <div>
                                <div className="flex justify-between items-start gap-2 mb-2">
                                    <h3 className="text-sm font-bold text-slate-100 group-hover:text-[#5fa8ff] transition-colors line-clamp-1">
                                        {item.title}
                                    </h3>
                                    <span className="text-[9px] text-slate-500 font-bold bg-[#001845] px-2 py-0.5 rounded-full whitespace-nowrap">
                                        ID: {item.id}
                                    </span>
                                </div>
                                <p className="text-xs text-slate-400 mb-4 line-clamp-2 leading-relaxed">
                                    {item.demands}
                                </p>
                            </div>
                            <div className="flex items-center justify-between mt-2 pt-3 border-t border-[#1e3d5f]/10">
                                <span className="text-[10px] text-slate-500 font-semibold">
                                    {new Date(item.created_at).toLocaleDateString('en-US', {
                                        month: 'short',
                                        day: 'numeric',
                                        year: 'numeric'
                                    })}
                                </span>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onShowConfirm(
                                                "Confirm Deletion",
                                                "This Job Description will be permanently deleted and cannot be recovered. Would you like to continue?",
                                                () => onDeleteHistoryItem(item.id)
                                            );
                                        }}
                                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-950/40 text-red-400 border border-red-800/50 hover:bg-red-900/60 hover:text-red-200 transition-all flex items-center justify-center gap-1"
                                    >
                                        <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                        <span>Delete</span>
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onSelectHistoryItem(item.id);
                                        }}
                                        className="bg-[#023E8A] hover:bg-[#3a7bd5] text-white text-[10px] font-bold px-3 py-1.5 rounded-md shadow-sm transition-colors"
                                    >
                                        View Report
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

/* ==========================================================================
   Interview Sessions Dashboard Component
   ========================================================================== */
const InterviewSessionsDashboard = () => {
    const [sessionsList, setSessionsList] = useState([]);
    const [selectedSession, setSelectedSession] = useState(null);
    const [candidatesList, setCandidatesList] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isActionLoading, setIsActionLoading] = useState(false);
    const [sessionSearch, setSessionSearch] = useState('');

    const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
    const [selectedCandidate, setSelectedCandidate] = useState(null);
    const [rawFeedback, setRawFeedback] = useState('');
    const [generalQuestions, setGeneralQuestions] = useState('');
    const [domainQuestions, setDomainQuestions] = useState('');
    const [feedbackError, setFeedbackError] = useState('');

    const [emailModalOpen, setEmailModalOpen] = useState(false);
    const [generatedEmail, setGeneratedEmail] = useState(null);

    const [prepKitModalOpen, setPrepKitModalOpen] = useState(false);
    const [prepKitQuestions, setPrepKitQuestions] = useState([]);

    const [consolidationModalOpen, setConsolidationModalOpen] = useState(false);
    const [consolidationData, setConsolidationData] = useState(null);

    const fetchSessions = async () => {
        setIsLoading(true);
        try {
            const res = await fetch('/api/sessions');
            if (res.ok) {
                const data = await res.json();
                setSessionsList(data);
            }
        } catch (e) {
            console.error("Error loading sessions:", e);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchCandidates = async (sessionId) => {
        setIsLoading(true);
        try {
            const res = await fetch(`/api/sessions/${sessionId}/candidates`);
            if (res.ok) {
                const data = await res.json();
                setCandidatesList(data);
            }
        } catch (e) {
            console.error("Error loading candidates:", e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();
    }, []);

    const handleSelectSession = (session) => {
        setSelectedSession(session);
        fetchCandidates(session.id);
    };

    const handleBackToSessions = () => {
        setSelectedSession(null);
        setCandidatesList([]);
        fetchSessions();
    };

    // Actions
    const handleAcceptReject = async (candidate, action) => {
        setIsActionLoading(true);
        try {
            const res = await fetch('/api/email-generation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: action,
                    candidate_name: candidate.name || "Candidate",
                    candidate_email: candidate.email || "candidate@example.com",
                    role_name: selectedSession.role,
                    prep_questions: []
                })
            });
            if (res.ok) {
                const data = await res.json();
                const emailObj = data.email ? data.email : data;
                setGeneratedEmail({
                    to: emailObj.to || candidate.email,
                    subject: emailObj.subject || `Application Update - ${selectedSession.role}`,
                    body_html: emailObj.body_html || emailObj.email_body_html || "<p>Email generated successfully.</p>"
                });
                setEmailModalOpen(true);
                fetchCandidates(selectedSession.id);
            } else {
                alert("Failed to run email generation.");
            }
        } catch (e) {
            console.error("Error generating email:", e);
        } finally {
            setIsActionLoading(false);
        }
    };

    const handleOpenFeedback = (candidate) => {
        setSelectedCandidate(candidate);
        setRawFeedback('');
        setGeneralQuestions('');
        setDomainQuestions('');
        setFeedbackError('');
        setFeedbackModalOpen(true);
    };

    const handleSaveQuestions = async () => {
        if (!generalQuestions.trim() && !domainQuestions.trim()) {
            setFeedbackError("Please enter at least one question to save.");
            return;
        }
        setIsActionLoading(true);
        setFeedbackError('');
        try {
            const res = await fetch('/api/master-questions/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    general_questions: generalQuestions.trim(),
                    domain_questions: domainQuestions.trim()
                })
            });
            if (res.ok) {
                // Also auto-save to session questions under the hood
                if (selectedSession && selectedCandidate) {
                    try {
                        await fetch('/api/session-questions/save', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                session_id: selectedSession.id,
                                candidate_id: selectedCandidate.id,
                                general_questions: generalQuestions.trim(),
                                domain_questions: domainQuestions.trim()
                            })
                        });
                        fetchCandidates(selectedSession.id);
                    } catch (err) {
                        console.error("Error auto-saving questions to session database:", err);
                    }
                }

                alert("pushed to Master Database");
                setGeneralQuestions('');
                setDomainQuestions('');
                setFeedbackModalOpen(false);
            } else {
                const data = await res.json();
                setFeedbackError(data.detail || "Failed to save questions to Master Database.");
            }
        } catch (e) {
            console.error("Error saving questions to master database:", e);
            setFeedbackError("Server connection error.");
        } finally {
            setIsActionLoading(false);
        }
    };

    const handleSendQuestions = async () => {
        if (!generalQuestions.trim() && !domainQuestions.trim()) {
            setFeedbackError("Please enter at least one question to send.");
            return;
        }
        setIsActionLoading(true);
        setFeedbackError('');
        try {
            const res = await fetch('/api/session-questions/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: selectedSession.id,
                    candidate_id: selectedCandidate.id,
                    general_questions: generalQuestions.trim(),
                    domain_questions: domainQuestions.trim()
                })
            });
            if (res.ok) {
                alert("send the questions to the next candidate");
                setGeneralQuestions('');
                setDomainQuestions('');
                
                // Advance to next candidate if available
                const currentIndex = candidatesList.findIndex(c => c.id === selectedCandidate.id);
                if (currentIndex !== -1 && currentIndex < candidatesList.length - 1) {
                    const nextCandidate = candidatesList[currentIndex + 1];
                    setSelectedCandidate(nextCandidate);
                    setFeedbackError('');
                } else {
                    setFeedbackModalOpen(false);
                }
                
                fetchCandidates(selectedSession.id);
            } else {
                const data = await res.json();
                setFeedbackError(data.detail || "Failed to send questions to the next candidate.");
            }
        } catch (e) {
            console.error("Error sending questions:", e);
            setFeedbackError("Server connection error.");
        } finally {
            setIsActionLoading(false);
        }
    };

    const handleAssemblePrepKit = async (candidate) => {
        setIsActionLoading(true);
        try {
            const sessRes = await fetch(`/api/sessions/${selectedSession.id}/questions`);
            const sessQuestions = sessRes.ok ? await sessRes.json() : [];

            const res = await fetch('/api/agent/progressive-prep', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    candidate_name: candidate.name || "Candidate",
                    role_name: selectedSession.role || "Role",
                    sequence_number: candidate.sequence_number || 1,
                    excel_baseline_questions: [],
                    previous_candidates_questions: sessQuestions.map(q => ({ question_text: q.standardized_question, category: q.category }))
                })
            });

            if (res.ok) {
                const data = await res.json();
                const questions = data.data ? data.data.prep_questions : (data.prep_questions || []);
                setPrepKitQuestions(questions);
                setSelectedCandidate(candidate);
                setPrepKitModalOpen(true);
            } else {
                alert("Failed to assemble prep kit.");
            }
        } catch (e) {
            console.error("Error assembling prep kit:", e);
        } finally {
            setIsActionLoading(false);
        }
    };

    const handleFinalConsolidation = async () => {
        setIsActionLoading(true);
        try {
            const histRes = await fetch('/api/master-questions');
            const histQuestions = histRes.ok ? await histRes.json() : [];

            const sessRes = await fetch(`/api/sessions/${selectedSession.id}/questions`);
            const sessQuestions = sessRes.ok ? await sessRes.json() : [];

            const res = await fetch('/api/final-consolidation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    all_session_questions: sessQuestions.map(q => ({ question_text: q.standardized_question, category: q.category })),
                    master_questions: histQuestions.map(q => ({ question_text: q.question_text, category: q.category, frequency_count: q.frequency_count }))
                })
            });

            if (res.ok) {
                const data = await res.json();
                setConsolidationData(data);
                setConsolidationModalOpen(true);
            } else {
                alert("Failed to run consolidation.");
            }
        } catch (e) {
            console.error("Error during final consolidation:", e);
        } finally {
            setIsActionLoading(false);
        }
    };

    return (
        <div className="flex-1 overflow-y-auto px-6 py-8 w-full animate-fade-in-up">
            <div className="flex items-center justify-between mb-8 border-b border-[#1e3d5f]/15 pb-4">
                <div className="flex items-center gap-3">
                    {selectedSession && (
                        <button onClick={handleBackToSessions} className="p-2 rounded-lg bg-[#001233] hover:bg-[#002855] text-slate-400 hover:text-white transition-colors">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                            </svg>
                        </button>
                    )}
                    <div>
                        <h1 className="text-lg md:text-xl font-bold text-slate-100 tracking-tight">
                            {selectedSession ? `Session: ${selectedSession.role}` : "Interview Sessions Pipeline"}
                        </h1>
                        <p className="text-xs text-slate-400 mt-1">
                            {selectedSession ? "Manage candidate interviews, standardization, and Insights consolidation." : "Select an active hiring session to evaluate candidates."}
                        </p>
                    </div>
                </div>
                {!selectedSession ? (
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <input
                                type="text"
                                value={sessionSearch}
                                onChange={(e) => setSessionSearch(e.target.value)}
                                placeholder="Search roles..."
                                className="bg-[#001233] border border-[#002855] focus:border-[#5fa8ff]/50 text-slate-100 placeholder-slate-500 text-xs rounded-lg pl-8 pr-3 py-2.5 w-48 focus:outline-none transition-colors"
                            />
                            <svg className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                            </svg>
                        </div>
                        <button
                            onClick={async () => {
                                const roleName = prompt("Enter new role title (e.g. Business Analyst (BA), PMO Lead, Asset Management PM):");
                                if (roleName && roleName.trim()) {
                                    try {
                                        const res = await fetch('/api/sessions', {
                                            method: 'POST',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify({ role: roleName.trim(), total_candidates: 0 })
                                        });
                                        if (res.ok) {
                                            fetchSessions();
                                        }
                                    } catch (e) {
                                        alert("Failed to create role session card.");
                                    }
                                }
                            }}
                            className="bg-[#023e8a] hover:bg-[#0077b6] text-slate-100 text-xs font-bold px-4 py-2.5 rounded-lg shadow-md transition-colors flex items-center gap-2"
                        >
                            <svg className="w-4 h-4 text-[#5fa8ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                            </svg>
                            <span>+ New Hiring Role</span>
                        </button>
                    </div>
                ) : (
                    <button
                        onClick={handleFinalConsolidation}
                        className="bg-[#5c2d5d] hover:bg-[#7e4280] text-slate-100 text-xs font-bold px-4 py-2.5 rounded-lg shadow-md transition-colors flex items-center gap-2"
                    >
                        <svg className="w-4 h-4 text-pink-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
                        </svg>
                        <span>Consolidate Insights</span>
                    </button>
                )}
            </div>

            {isLoading ? (
                <div className="flex justify-center items-center py-16">
                    <div className="w-8 h-8 border-4 border-[#5fa8ff]/20 border-top-color-[#5fa8ff] rounded-full animate-spin-custom"></div>
                </div>
            ) : !selectedSession ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {sessionsList
                        .filter(session => (session.role || "").toLowerCase().includes(sessionSearch.toLowerCase()))
                        .map(session => (
                        <div
                            key={session.id}
                            onClick={() => handleSelectSession(session)}
                            className="bg-[#001233] border border-[#002855] hover:border-[#5fa8ff]/30 rounded-xl p-5 shadow-md transition-all group cursor-pointer flex flex-col justify-between"
                        >
                            <div>
                                <div className="flex justify-between items-start mb-3">
                                    <h3 className="text-sm font-bold text-slate-100 group-hover:text-[#5fa8ff] transition-colors">{session.role}</h3>
                                    <span className="text-[9px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-bold">
                                        {session.status}
                                    </span>
                                </div>
                                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                                    Total candidates stacked: <strong>{session.total_candidates}</strong>
                                </p>
                            </div>
                            <div className="flex justify-end pt-3 border-t border-[#1e3d5f]/15">
                                <span className="text-[#5fa8ff] text-xs font-semibold group-hover:translate-x-1 transition-transform flex items-center gap-1">
                                    <span>Manage Session</span>
                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                                    </svg>
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="bg-[#001233] border border-[#002855] rounded-xl overflow-hidden shadow-md">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-[#001845]/50 text-slate-400 text-xs font-bold border-b border-[#002855]">
                                    <th className="p-4">Seq #</th>
                                    <th className="p-4">Name</th>
                                    <th className="p-4">Email</th>
                                    <th className="p-4">Score</th>
                                    <th className="p-4">Status</th>
                                    <th className="p-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[#002855]/40 text-slate-300 text-xs">
                                {candidatesList.map(candidate => (
                                    <tr key={candidate.id} className="hover:bg-[#001845]/20 transition-colors">
                                        <td className="p-4 font-bold text-[#5fa8ff]">Candidate #{candidate.sequence_number || 1}</td>
                                        <td className="p-4 font-semibold text-slate-100">{candidate.name || "N/A"}</td>
                                        <td className="p-4 text-slate-400">{candidate.email || "N/A"}</td>
                                        <td className="p-4">
                                            {candidate.resume_score ? (
                                                <span className={`font-bold ${candidate.resume_score >= 70 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                                    {candidate.resume_score}/100
                                                </span>
                                            ) : "N/A"}
                                        </td>
                                        <td className="p-4">
                                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${candidate.status === 'Accept' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                                    candidate.status === 'Reject' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                                                        'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                                }`}>
                                                {candidate.status || "Shortlisted"}
                                            </span>
                                        </td>
                                        <td className="p-4 text-right whitespace-nowrap">
                                            <div className="flex items-center justify-end gap-2 flex-nowrap whitespace-nowrap">
                                                <button
                                                    onClick={() => handleAcceptReject(candidate, 'ACCEPT')}
                                                    disabled={isActionLoading}
                                                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-2.5 py-1 rounded-md text-[10px] shadow-sm transition-colors whitespace-nowrap"
                                                >
                                                    Accept
                                                </button>
                                                <button
                                                    onClick={() => handleAcceptReject(candidate, 'REJECT')}
                                                    disabled={isActionLoading}
                                                    className="bg-rose-700 hover:bg-rose-600 text-white font-bold px-2.5 py-1 rounded-md text-[10px] shadow-sm transition-colors whitespace-nowrap"
                                                >
                                                    Reject
                                                </button>
                                                <button
                                                    onClick={() => handleOpenFeedback(candidate)}
                                                    disabled={isActionLoading}
                                                    className="bg-[#023e8a] hover:bg-[#0077b6] text-white font-bold px-2.5 py-1 rounded-md text-[10px] shadow-sm transition-colors whitespace-nowrap"
                                                >
                                                    Collect Questions
                                                </button>
                                                <button
                                                    onClick={() => handleAssemblePrepKit(candidate)}
                                                    disabled={isActionLoading}
                                                    className="bg-[#6b5b95] hover:bg-[#8675a9] text-white font-bold px-2.5 py-1 rounded-md text-[10px] shadow-sm transition-colors whitespace-nowrap"
                                                >
                                                    Prep Kit
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* MODAL: Collect Questions */}
            {feedbackModalOpen && (
                <div className="modal-overlay" onClick={() => setFeedbackModalOpen(false)}>
                    <div className="modal-content-box max-w-2xl" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="text-sm font-bold text-slate-100">Collect Questions: {selectedCandidate?.name}</h3>
                            <button className="modal-close-btn" onClick={() => setFeedbackModalOpen(false)}>✕</button>
                        </div>
                        <div className="modal-body space-y-4">
                            <p className="text-[11px] text-slate-400">
                                Enter the interview questions asked to the candidate. Standardized formatting will be applied dynamically.
                            </p>
                            <div className="grid grid-cols-2 gap-4">
                                {/* General Questions (Yellow Shade) */}
                                <div className="bg-[#1a140a] border border-amber-900/30 rounded-lg p-3 space-y-1.5">
                                    <label className="text-[11px] font-bold text-amber-400 uppercase tracking-wide">General Questions</label>
                                    <textarea
                                        value={generalQuestions}
                                        onChange={(e) => setGeneralQuestions(e.target.value)}
                                        placeholder="Enter standard/generic questions (one per line)..."
                                        rows={4}
                                        className="w-full bg-[#13121a] text-slate-100 border border-amber-800/30 rounded p-2 text-xs outline-none focus:border-amber-400/50"
                                    />
                                </div>
                                {/* Domain Questions (Green Shade) */}
                                <div className="bg-[#0a1a0f] border border-emerald-900/40 rounded-lg p-3 space-y-1.5">
                                    <label className="text-[11px] font-bold text-emerald-400 uppercase tracking-wide">Domain Questions</label>
                                    <textarea
                                        value={domainQuestions}
                                        onChange={(e) => setDomainQuestions(e.target.value)}
                                        placeholder="Enter role-specific/domain questions (one per line)..."
                                        rows={4}
                                        className="w-full bg-[#13121a] text-slate-100 border border-emerald-800/30 rounded p-2 text-xs outline-none focus:border-emerald-400/50"
                                    />
                                </div>
                            </div>
                            {feedbackError && (
                                <p className="text-xs text-rose-400 font-bold bg-rose-500/10 p-2 rounded-md border border-rose-500/20">{feedbackError}</p>
                            )}
                        </div>
                        <div className="modal-footer flex justify-end gap-2 p-4 border-t border-[#1e3d5f]/15">
                            <button onClick={() => setFeedbackModalOpen(false)} className="bg-transparent hover:bg-slate-800 text-slate-400 px-3 py-1.5 rounded-lg text-xs font-semibold">
                                Cancel
                            </button>
                            <button
                                onClick={handleSaveQuestions}
                                disabled={isActionLoading}
                                className="bg-amber-600 hover:bg-amber-500 text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-md transition-colors"
                            >
                                Save
                            </button>
                            <button
                                onClick={handleSendQuestions}
                                disabled={isActionLoading}
                                className="bg-[#023e8a] hover:bg-[#0077b6] text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-md transition-colors"
                            >
                                Send
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* MODAL: Email Preview */}
            {emailModalOpen && (
                <div className="modal-overlay" onClick={() => setEmailModalOpen(false)}>
                    <div className="modal-content-box max-w-2xl" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="text-sm font-bold text-slate-100">Generated Email: {generatedEmail?.to}</h3>
                            <button className="modal-close-btn" onClick={() => setEmailModalOpen(false)}>✕</button>
                        </div>
                        <div className="modal-body space-y-3">
                            <div className="text-xs border-b border-[#002855] pb-2">
                                <strong>Subject:</strong> {generatedEmail?.subject}
                            </div>
                            <div
                                className="bg-[#13121a] p-4 rounded-lg overflow-y-auto max-h-[300px] text-xs text-slate-300 leading-relaxed border border-slate-800"
                                dangerouslySetInnerHTML={{ __html: generatedEmail?.body_html || generatedEmail?.email_body_html }}
                            />
                        </div>
                        <div className="modal-footer flex justify-end p-4 border-t border-[#1e3d5f]/15">
                            <button onClick={() => setEmailModalOpen(false)} className="bg-[#023e8a] hover:bg-[#3a7bd5] text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-md">
                                Done
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* MODAL: Prep Kit Preview */}
            {prepKitModalOpen && (() => {
                const genericQs = prepKitQuestions.filter(q => q && !(q.category || '').toLowerCase().includes('domain'));
                const domainQs = prepKitQuestions.filter(q => q && (q.category || '').toLowerCase().includes('domain'));
                return (
                    <div className="modal-overlay" onClick={() => setPrepKitModalOpen(false)}>
                        <div className="modal-content-box max-w-3xl" onClick={(e) => e.stopPropagation()}>
                            <div className="modal-header">
                                <h3 className="text-sm font-bold text-slate-100">Client Interview Prep-Kit: {selectedCandidate?.name}</h3>
                                <button className="modal-close-btn" onClick={() => setPrepKitModalOpen(false)}>✕</button>
                            </div>
                            <div className="modal-body space-y-4">
                                <p className="text-[11px] text-slate-400">
                                    Merged & deduplicated set of client interview questions (limited to 15 questions max) partitioned for the candidate:
                                </p>
                                <div className="grid grid-cols-2 gap-4">
                                    {/* General Questions (Yellow Shade) */}
                                    <div className="bg-[#1a140a] border border-amber-900/30 rounded-lg p-3 space-y-2">
                                        <h4 className="text-xs font-bold text-amber-400 border-b border-amber-900/20 pb-1.5 uppercase tracking-wide">General Questions</h4>
                                        <div className="max-h-[260px] overflow-y-auto space-y-1.5">
                                            {genericQs.length === 0 ? (
                                                <p className="text-[10px] text-slate-500 italic">No general questions.</p>
                                            ) : (
                                                <ol className="list-decimal list-inside text-xs text-slate-300 space-y-2">
                                                    {genericQs.map((q, idx) => (
                                                        <li key={idx} className="leading-relaxed">
                                                            <span className="font-semibold text-slate-100">{stripQuestionTags(q.question_text)}</span>
                                                            <span className="text-[8px] bg-[#002855] text-[#5fa8ff] px-1.5 py-0.5 rounded-full ml-1 font-bold select-none">{q.category}</span>
                                                        </li>
                                                    ))}
                                                </ol>
                                            )}
                                        </div>
                                    </div>
                                    {/* Domain Questions (Green Shade) */}
                                    <div className="bg-[#0a1a0f] border border-emerald-900/40 rounded-lg p-3 space-y-2">
                                        <h4 className="text-xs font-bold text-emerald-400 border-b border-emerald-900/20 pb-1.5 uppercase tracking-wide">Domain Questions</h4>
                                        <div className="max-h-[260px] overflow-y-auto space-y-1.5">
                                            {domainQs.length === 0 ? (
                                                <p className="text-[10px] text-slate-500 italic">No domain questions.</p>
                                            ) : (
                                                <ol className="list-decimal list-inside text-xs text-slate-300 space-y-2">
                                                    {domainQs.map((q, idx) => (
                                                        <li key={idx} className="leading-relaxed">
                                                            <span className="font-semibold text-slate-100">{stripQuestionTags(q.question_text)}</span>
                                                            <span className="text-[8px] bg-emerald-950 text-emerald-400 px-1.5 py-0.5 rounded-full ml-1 font-bold select-none">{q.category}</span>
                                                        </li>
                                                    ))}
                                                </ol>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="modal-footer flex justify-end p-4 border-t border-[#1e3d5f]/15">
                                <button onClick={() => setPrepKitModalOpen(false)} className="bg-[#023e8a] hover:bg-[#3a7bd5] text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-md">
                                    Done
                                </button>
                            </div>
                        </div>
                    </div>
                );
            })()}
            {/* MODAL: Consolidation Details */}
            {consolidationModalOpen && (() => {
                const genericCats = (consolidationData?.pdf_structure?.categories || []).filter(c => c && !(c.name || c.category || '').toLowerCase().includes('domain'));
                const domainCats = (consolidationData?.pdf_structure?.categories || []).filter(c => c && (c.name || c.category || '').toLowerCase().includes('domain'));
                return (
                    <div className="modal-overlay" onClick={() => setConsolidationModalOpen(false)}>
                        <div className="modal-content-box max-w-3xl" onClick={(e) => e.stopPropagation()}>
                            <div className="modal-header">
                                <h3 className="text-sm font-bold text-slate-100">Consolidated Client Interview Insights</h3>
                                <button className="modal-close-btn" onClick={() => setConsolidationModalOpen(false)}>✕</button>
                            </div>
                            <div className="modal-body space-y-4">
                                <div className="border border-slate-800 rounded-lg p-3 bg-[#13121a]">
                                    <h4 className="text-xs font-bold text-slate-200 mb-3 border-b border-slate-800 pb-1.5 text-pink-300">
                                        {consolidationData?.pdf_structure?.title}
                                    </h4>
                                    
                                    <div className="grid grid-cols-2 gap-4">
                                        {/* General Column (Yellow) */}
                                        <div className="bg-[#1a140a] border border-amber-900/30 rounded-lg p-3 space-y-2">
                                            <h4 className="text-xs font-bold text-amber-400 border-b border-amber-900/20 pb-1.5 uppercase tracking-wide">General Questions</h4>
                                            <div className="max-h-[220px] overflow-y-auto space-y-2">
                                                {genericCats.length === 0 ? (
                                                    <p className="text-[10px] text-slate-500 italic">No general questions consolidated.</p>
                                                ) : (
                                                    genericCats.map((cat, idx) => (
                                                        <div key={idx}>
                                                            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{cat ? (cat.name || cat.category) : ''}</span>
                                                            <ul className="list-disc list-inside text-xs text-slate-300 pl-1 mt-1 space-y-1">
                                                                {cat && cat.questions && cat.questions.map((q, qidx) => (
                                                                    <li key={qidx} className="leading-relaxed">{q}</li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        </div>
                                        {/* Domain Column (Green) */}
                                        <div className="bg-[#0a1a0f] border border-emerald-900/40 rounded-lg p-3 space-y-2">
                                            <h4 className="text-xs font-bold text-emerald-400 border-b border-emerald-900/20 pb-1.5 uppercase tracking-wide">Domain Questions</h4>
                                            <div className="max-h-[220px] overflow-y-auto space-y-2">
                                                {domainCats.length === 0 ? (
                                                    <p className="text-[10px] text-slate-500 italic">No domain questions consolidated.</p>
                                                ) : (
                                                    domainCats.map((cat, idx) => (
                                                        <div key={idx}>
                                                            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{cat ? (cat.name || cat.category) : ''}</span>
                                                            <ul className="list-disc list-inside text-xs text-slate-300 pl-1 mt-1 space-y-1">
                                                                {cat && cat.questions && cat.questions.map((q, qidx) => (
                                                                    <li key={qidx} className="leading-relaxed">{q}</li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Updates to Master Database:</h4>
                                    <div className="bg-[#13121a] p-3 rounded-lg border border-slate-800 max-h-[140px] overflow-y-auto space-y-2">
                                        {consolidationData?.updates_to_master?.map((up, idx) => (
                                            <div key={idx} className="flex justify-between items-center text-xs border-b border-slate-800/40 pb-1.5">
                                                <div>
                                                    <span className="font-semibold text-slate-200">{stripQuestionTags(up.question_text)}</span>
                                                    <span className="text-[9px] text-slate-500 ml-2">({up.category})</span>
                                                </div>
                                                <div className="flex items-center gap-1.5">
                                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${up.action === 'INSERT' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>
                                                        {up.action}
                                                    </span>
                                                    <span className="text-[10px] text-slate-400 font-bold">Freq: {up.frequency_count}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                            <div className="modal-footer flex justify-end p-4 border-t border-[#1e3d5f]/15">
                                <button onClick={() => setConsolidationModalOpen(false)} className="bg-[#023e8a] hover:bg-[#3a7bd5] text-white px-4 py-1.5 rounded-lg text-xs font-bold shadow-md">
                                    Done
                                </button>
                            </div>
                        </div>
                    </div>
                );
            })()}
        </div>
    );
};

/* ==========================================================================
   ChatHeader Component (Oxford Blue styling)
   ========================================================================== */
const ChatHeader = ({ title, toggleSidebar }) => {
    return (
        <header className="h-[64px] bg-[#0a0f1c] border-b border-[#1e3d5f]/20 px-4 md:px-6 flex items-center justify-between z-10 flex-shrink-0">
            <div className="flex items-center gap-3">
                {/* Menu trigger (all screen sizes) */}
                <button className="text-slate-400 hover:text-white p-1 rounded-lg" onClick={toggleSidebar}>
                    <MenuIcon />
                </button>
                {title && title.trim() === 'Saved Job Descriptions' ? (
                    <div className="flex items-center h-8 w-[110px]">
                        <img
                            src="/assests/Protiviti_logo1.webp"
                            alt="Protiviti"
                            className="max-w-full h-auto object-contain block"
                            style={{ filter: 'brightness(0) invert(1)' }}
                            onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = '/static/Protiviti_logo1.webp'; }}
                        />
                    </div>
                ) : (
                    <h2 className="text-sm font-semibold text-slate-100 truncate max-w-[200px] md:max-w-md">{title}</h2>
                )}
            </div>
        </header>
    );
};

/* ==========================================================================
   EmptyStateHero Component (No avatar, suggestions removed)
   ========================================================================== */
const EmptyStateHero = ({ onSelectSession }) => {
    const features = [
        {
            key: 'session-new-jd',
            title: 'New JD',
            desc: 'Create a new Job Description, parse client requirements, and upload candidate resumes.',
            icon: (
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            ),
        },
        {
            key: 'session-saved',
            title: 'Saved JD',
            desc: 'View and reopen previously generated job descriptions.',
            icon: (
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            ),
        },
        {
            key: 'session-interviews',
            title: 'Interview Session',
            desc: 'Conduct AI-powered interviews and evaluate candidates fairly.',
            icon: (
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            ),
        },
        {
            key: 'session-role-alignment',
            title: 'Role Alignment',
            desc: 'Match the right talent with the right roles.',
            icon: (
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 9m0 8V9m0 0L9 7" />
            ),
        },
        {
            key: 'session-client-feedback',
            title: 'Client Feedback',
            desc: 'Collect feedback and improve hiring continuously.',
            icon: (
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            ),
        },
        {
            key: 'session-resume-standardizer',
            title: 'Resume Standardization Tool',
            desc: 'Convert candidate CVs to standard Protiviti profiles in the background.',
            icon: (
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            ),
        },
    ];

    return (
        <div className="flex-1 overflow-y-auto w-full flex flex-col justify-start">
            <div className="w-full max-w-5xl mx-auto px-4 py-4">
                {/* Title */}
                <div className="text-center mb-5">
                    <h1 className="text-2xl md:text-3xl font-bold tracking-tight mb-2">
                        <span className="text-white">Welcome to Protiviti </span>
                        <span className="text-[#5fa8ff]">Recruitment Site</span>
                    </h1>
                    <p className="text-xs md:text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
                        Your AI-powered hiring assistant for smarter, faster and more confident recruitment decisions.
                    </p>
                </div>

                {/* Feature cards */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-5 items-stretch">
                    {features.map((f, i) => (
                        <button
                            key={i}
                            onClick={() => onSelectSession && onSelectSession(f.key)}
                            className="h-full bg-[#001233] border border-[#002855] hover:border-[#5fa8ff]/40 rounded-xl p-4 flex flex-col items-center text-center transition-colors"
                        >
                            <div className="w-11 h-11 rounded-full bg-[#001845] border border-[#002855] flex items-center justify-center mb-3">
                                <svg className="w-5 h-5 text-[#5fa8ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                    {f.icon}
                                </svg>
                            </div>
                            <h3 className="text-xs font-bold text-slate-100 mb-1.5">{f.title}</h3>
                            <p className="text-[10px] text-slate-400 leading-relaxed">{f.desc}</p>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};

/* ==========================================================================
   NewJDScreen Component (Dedicated screen for demands & resumes)
   ========================================================================== */
const NewJDScreen = ({ onSend, onUpload }) => {
    const [clientDetails, setClientDetails] = useState('');
    const fileRef = useRef(null);

    const handleSubmitDetails = () => {
        if (!clientDetails.trim()) return;
        if (onSend) onSend(clientDetails.trim());
        setClientDetails('');
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files.length > 0 && onUpload) {
            onUpload(e.target.files, 'groq', '');
        }
    };

    return (
        <div className="flex-1 overflow-y-auto w-full flex flex-col justify-start animate-fade-in-up">
            <div className="w-full max-w-3xl mx-auto px-4 py-8">
                {/* Title */}
                <div className="text-center mb-6">
                    <h1 className="text-2xl md:text-3xl font-bold tracking-tight mb-2">
                        <span className="text-white">Create New </span>
                        <span className="text-[#5fa8ff]">Job Description</span>
                    </h1>
                    <p className="text-xs md:text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
                        Input your client's requirements to generate a complete Job Description, or upload candidate resumes for screening.
                    </p>
                </div>

                {/* Enter Client's Demands box */}
                <div className="bg-[#001233] border border-[#002855] rounded-xl p-5 mb-6">
                    <label className="block text-sm font-bold text-slate-100 mb-2">Enter Client's Demands</label>
                    <div className="flex flex-col gap-3">
                        <textarea
                            value={clientDetails}
                            onChange={(e) => setClientDetails(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmitDetails(); } }}
                            placeholder="e.g. We are looking for a Data Analyst with 3+ years of experience in SQL, Power BI, and data visualization..."
                            rows={4}
                            className="w-full bg-[#0a0f1c] text-slate-100 border border-[#002855] rounded-lg p-3 text-xs outline-none focus:border-[#5fa8ff]/50 resize-none leading-relaxed placeholder-slate-500"
                        />
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] text-slate-500">Press Shift + Enter for a new line.</span>
                            <button
                                onClick={handleSubmitDetails}
                                disabled={!clientDetails.trim()}
                                className="flex items-center gap-2 bg-[#023E8A] hover:bg-[#3a7bd5] disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold px-6 py-2.5 rounded-lg shadow-md transition-colors"
                            >
                                <ArrowUpIcon className="w-3.5 h-3.5" />
                                <span>Generate JD</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Let's get started box */}
                <div className="border-2 border-dashed border-[#002855] rounded-2xl p-6 flex flex-col items-center text-center">
                    <svg className="w-10 h-10 text-[#5fa8ff] mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <h2 className="text-base font-bold text-slate-100 mb-1">Upload Candidate Resumes</h2>
                    <p className="text-xs text-slate-400 mb-4 max-w-md">
                        Please generate a Job Description first or select a saved one, then upload resumes to begin matching and evaluation.
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-3">
                        <button
                            onClick={() => fileRef.current && fileRef.current.click()}
                            className="flex items-center gap-2 bg-transparent hover:bg-[#001845] text-slate-100 border border-[#002855] text-xs font-bold px-6 py-2.5 rounded-lg transition-colors"
                        >
                            <svg className="w-4 h-4 text-[#5fa8ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            <span>Upload Resume (PDF only)</span>
                        </button>
                        <input
                            type="file"
                            accept=".pdf"
                            multiple
                            style={{ display: 'none' }}
                            ref={fileRef}
                            onChange={handleFileChange}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

/* ==========================================================================
   Helper: extract candidate's real name from resume text
   ========================================================================== */
const extractCandidateName = (cvText, filename) => {
    if (cvText && cvText.trim()) {
        const lines = cvText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        // A real name: 2-4 words, each starting with a capital letter, no digits or special chars
        const nameRegex = /^([A-Z][a-zA-Z'-]+)(\s[A-Z][a-zA-Z'-]+){1,3}$/;
        for (let i = 0; i < Math.min(lines.length, 8); i++) {
            const line = lines[i];
            // Skip lines that look like roles, titles, or contact info
            if (/[|•@\d\/\\:,]/.test(line)) continue;
            if (/resume|curriculum|vitae|profile|summary|linkedin|objective|address/i.test(line)) continue;
            if (nameRegex.test(line)) return line;
        }
    }
    // Fallback to filename without extension
    return filename ? filename.replace(/\.[^/.]+$/, "").replace(/[_-]+/g, " ").trim() : "Applicant";
};

/* ==========================================================================
   GeneratedContentCard Component (Oxford Blue styling)
   ========================================================================== */
const GeneratedContentCard = ({ rawText, cvText, filename, onViewResume, jdTitle, matchedRole }) => {
    const [copied, setCopied] = useState(false);

    const parseJD = (text) => {
        const lines = text.split('\n');
        let jobTitle = "";
        let cleanedLines = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.toLowerCase().includes("job title:") || line.toLowerCase().startsWith("1. job title") || line.toLowerCase().includes("role:")) {
                const parts = line.split(/:(.+)/);
                if (parts.length > 1 && parts[1].trim()) {
                    jobTitle = parts[1].trim().replace(/\*/g, '');
                }
                continue;
            }
            if (!jobTitle && line.startsWith("# ")) {
                jobTitle = line.replace(/^#+\s*/, '').replace(/\*/g, '').trim();
            }
            cleanedLines.push(lines[i]);
        }

        // If jobTitle is missing or default generic string, extrapolate dynamically matching Excel headings
        if (!jobTitle || jobTitle.toLowerCase().includes("report") || jobTitle.toLowerCase().includes("analyzer")) {
            const lowerText = (text + " " + (filename || "")).toLowerCase();
            const hasWord = (word) => {
                const regex = new RegExp('\\b' + word + '\\b', 'i');
                return regex.test(lowerText);
            };

            if (lowerText.includes("asset management")) {
                jobTitle = "Asset Management PM";
            } else if (lowerText.includes("transaction banking")) {
                jobTitle = "Transaction Banking PMO";
            } else if (hasWord("pmo")) {
                jobTitle = "PMO Lead";
            } else if (lowerText.includes("lending")) {
                jobTitle = "Lending BA";
            } else if (lowerText.includes("gen ai") || lowerText.includes("genai")) {
                if (hasWord("pm") || lowerText.includes("project manager") || lowerText.includes("product manager")) {
                    jobTitle = "Gen AI PM";
                } else {
                    jobTitle = "Gen AI BA";
                }
            } else if (hasWord("pm") || lowerText.includes("project manager")) {
                jobTitle = "Project Manager (PM)";
            } else if (hasWord("ba") || lowerText.includes("business analyst")) {
                jobTitle = "Business Analyst (BA)";
            } else if (lowerText.includes("cloud") || hasWord("aws") || hasWord("azure")) {
                jobTitle = "Cloud Solutions Architect";
            } else if (filename) {
                jobTitle = filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ") + " Role";
            } else {
                jobTitle = "Business Analyst (BA)";
            }
        }

        const bodyText = cleanedLines.join('\n').trim();
        let bodyHtml = bodyText;

        // 1. Format Overall Match Score: make the label bold, and color the score based on thresholds
        bodyHtml = bodyHtml.replace(/Overall Match Score:\s*(\d+)\/100/g, (match, scoreStr) => {
            const score = parseInt(scoreStr, 10);
            let colorClass = "text-rose-400";
            if (score >= 70) {
                colorClass = "text-emerald-400";
            } else if (score >= 40) {
                colorClass = "text-amber-400";
            }
            return `**Overall Match Score:** <span class="${colorClass} font-bold">${score}/100</span>`;
        });

        // 2. Format Recommendation status with green/red colors
        bodyHtml = bodyHtml.replace(/Status:\s*(?:\*\*)?(Interview|Shortlist|Reject)(?:\*\*)?/gi, (match, status) => {
            const lowerStatus = status.toLowerCase();
            let colorClass = "text-slate-100";
            if (lowerStatus === 'interview' || lowerStatus === 'shortlist') {
                colorClass = "text-emerald-400";
            } else if (lowerStatus === 'reject') {
                colorClass = "text-rose-400";
            }
            return `Status: <span class="${colorClass} font-bold">${status}</span>`;
        });

        // 3. Format tick marks (✔) and cross marks (✘) with green/red colors
        bodyHtml = bodyHtml.replace(/✔/g, '<span class="text-emerald-400 font-bold mr-1">✔</span>');
        bodyHtml = bodyHtml.replace(/✘/g, '<span class="text-rose-400 font-bold mr-1">✘</span>');

        bodyHtml = bodyHtml
            .replace(/\n/g, "<br>")
            .replace(/(?:<br>|^)(?:\d+\.\s+)?(Role Overview|Key Responsibilities|Required Skills.*?|Preferred Experience|Qualifications)(?::)?/gi, (match, headerName) => {
                let iconName = "info";
                const lowerHeader = headerName.toLowerCase();
                if (lowerHeader.includes("responsibilities")) iconName = "list-todo";
                else if (lowerHeader.includes("skills") || lowerHeader.includes("qualifications")) iconName = "award";
                else if (lowerHeader.includes("experience")) iconName = "briefcase";

                return `<br><h3 class="text-slate-100 font-semibold text-xs border-b border-[#002855] pb-1 mt-4 mb-2 flex items-center gap-1.5"><i data-icon="${iconName}"></i>${headerName}</h3>`;
            })
            .replace(/\*\*(.*?)\*\*/g, "<strong class='text-slate-100 font-medium'>$1</strong>")
            .replace(/(?:<br>)\s*[-*•]\s*(.*?)(?=<br>|$)/g, "<li class='pl-4 relative before:content-[\"▪\"] before:text-[#5fa8ff] before:absolute before:left-0 before:top-0 text-xs mt-1'>$1</li>");

        return { bodyHtml, jobTitle };
    };

    const parsed = parseJD(rawText);

    const handleCopy = () => {
        let textToCopy = parsed.bodyHtml
            .replace(/<br\s*\/?>/gi, '\n')
            .replace(/<h3>.*?<\/h3>/g, (match) => '\n' + match.replace(/<[^>]*>/g, '') + '\n')
            .replace(/<li>(.*?)<\/li>/g, '- $1\n')
            .replace(/<[^>]*>/g, '')
            .trim();

        const fullText = `${parsed.jobTitle}\nAnalyzed by Protiviti AI\n=========================================\n${textToCopy}`;

        navigator.clipboard.writeText(fullText).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    useEffect(() => {
        const iconElements = document.querySelectorAll('[data-icon]');
        iconElements.forEach(el => {
            const type = el.getAttribute('data-icon');
            el.className = "w-3.5 h-3.5 text-[#5fa8ff] inline-block mr-1.5";
            if (type === 'info') {
                el.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" fill="none" />';
            } else if (type === 'list-todo') {
                el.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" stroke="currentColor" fill="none" />';
            } else if (type === 'award') {
                el.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138z" stroke="currentColor" fill="none" />';
            } else if (type === 'briefcase') {
                el.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" stroke="currentColor" fill="none" />';
            }
            el.outerHTML = `<svg class="${el.className}" viewBox="0 0 24 24">${el.innerHTML}</svg>`;
        });
    }, [parsed.bodyHtml]);

    const formattedDate = new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });

    return (
        <div className="bg-[#001233] border border-[#002855] rounded-xl overflow-hidden shadow-md mt-2 animate-fade-in-up">
            {/* Header */}
            <div className="bg-[#001845]/40 px-4 py-3 border-b border-[#002855] flex justify-between items-start gap-4">
                <div className="flex flex-col gap-0.5">
                    <h3 className="text-sm font-bold text-slate-100">{cvText ? extractCandidateName(cvText, filename) : parsed.jobTitle}</h3>
                    <span className="text-[10px] text-slate-500 font-medium">
                        Analyzed by Protiviti AI • {formattedDate}
                    </span>
                </div>
                {cvText ? (
                    <button
                        onClick={() => onViewResume(cvText, filename, true)}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[10px] font-bold border bg-[#001233] border-[#002855] hover:border-[#5fa8ff] text-slate-400 hover:text-slate-200 transition-colors"
                    >
                        <svg className="w-3.5 h-3.5 text-[#5fa8ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        <span>View Resume</span>
                    </button>
                ) : (
                    <button
                        onClick={handleCopy}
                        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[10px] font-bold border transition-colors ${copied ? 'bg-emerald-500/10 border-emerald-500 text-emerald-400' : 'bg-[#001233] border-[#002855] hover:border-[#5fa8ff] text-slate-400 hover:text-slate-200'}`}
                    >
                        {copied ? <CheckIcon className="w-3 h-3" /> : <CopyIcon className="w-3 h-3" />}
                        <span>{copied ? 'Copied!' : 'Copy JD'}</span>
                    </button>
                )}
            </div>

            {/* Content */}
            <div
                className="p-4 text-xs text-slate-300 leading-snug space-y-1 list-none pb-2"
                dangerouslySetInnerHTML={{ __html: parsed.bodyHtml }}
            />

            {/* Accept/Reject actions inline for resume evaluation cards */}
            {rawText.includes("Overall Match Score:") && (
                <div className="px-4 pb-4 flex gap-2 border-t border-[#002855]/40 pt-3">
                    <button
                        onClick={async () => {
                            try {
                                const scoreMatch = rawText.match(/Overall Match Score:\s*(\d+)/);
                                const score = scoreMatch ? parseInt(scoreMatch[1], 10) : 85;

                                const statusMatch = rawText.match(/Status:\s*(Interview|Shortlist|Reject)/i);
                                const status = statusMatch ? statusMatch[1] : "Shortlist";

                                const reasoningMatch = rawText.match(/Reasoning:\s*([^\n]+)/i);
                                const reasoning = reasoningMatch ? reasoningMatch[1] : "Matched skills.";

                                const candName = extractCandidateName(cvText, filename);

                                const res = await fetch('/api/candidates/accept', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        name: candName,
                                        email: candName.toLowerCase().replace(/\s+/g, '') + '@example.com',
                                        role: matchedRole || (jdTitle && !["Resume Analyzer", "New Analyzer", "Saved Job Descriptions"].includes(jdTitle)) ? (matchedRole || jdTitle) : (parsed.jobTitle && parsed.jobTitle !== "Resume Evaluation Report" ? parsed.jobTitle : 'Transaction Banking (Payments BA)'),
                                        resume_text: cvText || rawText,
                                        resume_score: score,
                                        reasoning: reasoning
                                    })
                                });
                                if (res.ok) {
                                    const data = await res.json();
                                    const htmlContent = data.email ? (data.email.body_html || data.email.email_body_html) : (data.body_html || data.email_body_html);
                                    onViewResume(
                                        htmlContent,
                                        `Acceptance Email & Prep-Kit for ${candName}`
                                    );
                                } else {
                                    alert("Failed to accept candidate.");
                                }
                            } catch (e) {
                                alert("Error accepting candidate.");
                            }
                        }}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold px-3 py-1.5 rounded-md shadow-sm transition-colors"
                    >
                        Accept Candidate
                    </button>
                    <button
                        onClick={async () => {
                            try {
                                const candName = extractCandidateName(cvText, filename);
                                const res = await fetch('/api/email-generation', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        action: 'REJECT',
                                        candidate_name: candName,
                                        candidate_email: candName.toLowerCase().replace(/\s+/g, '') + '@example.com',
                                        role_name: parsed.jobTitle || 'Business Analyst (BA)'
                                    })
                                });
                                if (res.ok) {
                                    const data = await res.json();
                                    const htmlContent = data.email ? (data.email.body_html || data.email.email_body_html) : (data.body_html || data.email_body_html);
                                    onViewResume(
                                        htmlContent,
                                        `Rejection Email for ${candName}`
                                    );
                                } else {
                                    alert("Failed to reject candidate.");
                                }
                            } catch (e) {
                                alert("Error generating rejection email.");
                            }
                        }}
                        className="bg-rose-700 hover:bg-rose-600 text-white text-[10px] font-bold px-3 py-1.5 rounded-md shadow-sm transition-colors"
                    >
                        Reject Candidate
                    </button>
                </div>
            )}
        </div>
    );
};

/* ==========================================================================
   ChatBubble Component (Sizing Locked on Edit, Read-Only Bot Card JDs)
   ========================================================================== */
const ChatBubble = ({ message, onSaveEdit, onViewResume, jdTitle }) => {
    const isUser = message.sender === 'user';
    const [isEditing, setIsEditing] = useState(false);
    const [editText, setEditText] = useState(message.text);

    const handleSave = () => {
        if (editText.trim() && editText.trim() !== message.text) {
            onSaveEdit(message.id, editText);
        }
        setIsEditing(false);
    };

    const handleCancel = () => {
        setEditText(message.text);
        setIsEditing(false);
    };

    if (isUser) {
        return (
            <div className="group flex items-start gap-3 w-full self-end flex-row-reverse relative animate-fade-in-up">
                <div className="w-7 h-7 rounded-lg bg-[#001845] border border-[#1e3d5f]/30 flex items-center justify-center flex-shrink-0 text-slate-300 shadow-sm">
                    <UserIcon className="w-3.5 h-3.5 text-[#5fa8ff]" />
                </div>

                {/* Edit Action Button exposed on hover */}
                {!isEditing && (
                    <button
                        onClick={() => setIsEditing(true)}
                        className="group-hover:opacity-100 opacity-0 transition-opacity duration-200 w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer bg-[#ccd5ae] border border-[#a3b18a]/30 text-black flex-shrink-0"
                        title="Edit message"
                    >
                        <EditIcon className="w-4 h-4 text-black" />
                    </button>
                )}

                {isEditing ? (
                    /* Enforce exact same width constraints to keep chatbox size locked */
                    <div className="bg-[#023e8a] text-slate-100 text-xs px-4 py-3 rounded-2xl rounded-tr-sm shadow-md leading-snug w-[600px] max-w-[85vw] flex flex-col">
                        <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSave();
                                } else if (e.key === 'Escape') {
                                    handleCancel();
                                }
                            }}
                            onBlur={handleSave}
                            autoFocus
                            rows={Math.max(2, Math.ceil(editText.length / 85))}
                            className="bg-transparent text-white text-xs w-full resize-none outline-none border-none p-0 focus:ring-0 leading-snug"
                        />
                    </div>
                ) : (
                    /* Keep bubble layout identical in size (w-[600px] max-w-[85vw]) */
                    <div className="bg-[#023e8a] text-slate-100 text-xs px-4 py-3 rounded-2xl rounded-tr-sm shadow-md leading-snug w-[600px] max-w-[85vw] break-words">
                        {message.text}
                    </div>
                )}
            </div>
        );
    }

    return (
        /* Bot generated JD cards have edit icon removed and are read-only */
        <div className="group flex items-start gap-3 w-full relative animate-fade-in-up">
            <div className="w-7 h-7 rounded-lg bg-[#5fa8ff] flex items-center justify-center flex-shrink-0 text-[#001233] shadow-sm">
                <SparklesIcon className="w-3.5 h-3.5" />
            </div>

            <div className="flex-1 min-w-0">
                {message.isError ? (
                    <div className="bg-[#5c1d24]/20 border border-[#b23b3b]/30 text-[#ff7b7b] text-xs px-4 py-3 rounded-xl">
                        {message.text}
                    </div>
                ) : message.isProcessing ? (
                    <div className="flex items-center gap-2.5 text-xs text-slate-500 font-semibold py-1">
                        <div className="w-3.5 h-3.5 border-2 border-[#5fa8ff]/20 border-top-color-[#5fa8ff] rounded-full animate-spin-custom"></div>
                        <span>{message.text || "Analyzing requirements and compiling report..."}</span>
                    </div>
                ) : (
                    <div>
                        <GeneratedContentCard
                            rawText={message.text}
                            cvText={message.cv_text}
                            filename={message.filename}
                            onViewResume={onViewResume}
                            jdTitle={jdTitle}
                            matchedRole={message.matched_role}
                        />
                        {message.keywords && message.keywords.length > 0 && (
                            <div className="mt-2.5 flex flex-wrap gap-1.5 items-center px-1">
                                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider select-none">Keywords:</span>
                                {message.keywords.map((kw, idx) => (
                                    <span
                                        key={idx}
                                        className="bg-[#002855] text-[#5fa8ff] border border-[#1e3d5f]/25 px-2 py-0.5 rounded-full text-[10px] font-semibold transition-colors hover:border-[#5fa8ff]/50"
                                    >
                                        {kw}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

/* ==========================================================================
   PromptInputBar Component (Dark image shade capsule #13121a, transitions on hover)
   ========================================================================== */
const PromptInputBar = ({ onSend, onUpload, isLoading, hasJd }) => {
    const [text, setText] = useState('');
    const [isDragging, setIsDragging] = useState(false);
    const [provider, setProvider] = useState('groq');
    const [missingKeywords, setMissingKeywords] = useState('');
    const textareaRef = useRef(null);
    const fileInputRef = useRef(null);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleSubmit = () => {
        if (!text.trim() || isLoading) return;
        onSend(text);
        setText('');
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        if (hasJd) {
            setIsDragging(true);
        }
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        if (!hasJd) return;
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            onUpload(e.dataTransfer.files, provider, missingKeywords);
        }
    };

    const handleZoneClick = () => {
        if (!hasJd) {
            alert("Please generate a Job Description first before uploading a resume.");
            return;
        }
        if (fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            onUpload(e.target.files, provider, missingKeywords);
        }
    };

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 140) + 'px';
        }
    }, [text]);

    return (
        <div className="bg-[#0a0f1c] border-t border-[#1e3d5f]/20 p-4 flex-shrink-0 z-10">
            <div className="max-w-3xl mx-auto w-full flex flex-col gap-2">
                {/* Missing Keywords box (used to screen CVs alongside the demand) */}
                <div className={`${!hasJd ? 'opacity-40' : ''}`}>
                    <label className="flex items-center gap-1.5 text-[10px] font-bold text-[#5fa8ff] uppercase tracking-wider mb-1">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5a1.99 1.99 0 011.414.586l7 7a2 2 0 010 2.828l-5 5a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                        Missing Keywords <span className="text-slate-500 font-normal normal-case">(next-cycle skills to screen CVs against — comma separated)</span>
                    </label>
                    <textarea
                        value={missingKeywords}
                        onChange={(e) => setMissingKeywords(e.target.value)}
                        disabled={!hasJd}
                        placeholder="e.g. SWIFT gpi, FX settlement, stakeholder management, war-room escalation"
                        rows={2}
                        className="w-full bg-[#001233] text-slate-100 border border-[#002855] rounded-lg p-2.5 text-xs outline-none focus:border-[#5fa8ff]/50 resize-none leading-relaxed disabled:cursor-not-allowed"
                    />
                </div>

                {/* Drag and Drop Zone */}
                <div
                    id="drop-zone"
                    onClick={handleZoneClick}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`${isDragging ? 'dragging' : ''} ${!hasJd ? 'opacity-40 cursor-not-allowed' : ''}`}
                >
                    <svg className="w-6 h-6 text-[#5fa8ff] mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <span className="text-xs">
                        {hasJd
                            ? "Drag & Drop Resume PDF here or Click to upload"
                            : "Generate a Job Description first to enable Resume Upload"
                        }
                    </span>
                    <input
                        type="file"
                        id="file-input"
                        accept=".pdf"
                        multiple
                        style={{ display: 'none' }}
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        disabled={!hasJd}
                    />
                </div>

                {/* Text Input Wrapper */}
                <div className="flex flex-col gap-2 bg-[#13121a] hover:bg-[#181720] focus-within:bg-[#181720] border border-slate-800/80 hover:border-[#5fa8ff]/30 focus-within:border-[#5fa8ff]/50 rounded-[28px] px-5 py-2.5 shadow-lg transition-all duration-300">
                    <div className="flex items-center justify-between w-full">
                        <textarea
                            id="userInput"
                            ref={textareaRef}
                            rows="1"
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Enter Client's Demands"
                            className="flex-1 bg-transparent border-none text-slate-100 placeholder-slate-500 resize-none outline-none text-xs min-h-[38px] max-h-[140px] py-2"
                            disabled={isLoading}
                        />

                        <div className="flex items-center gap-3">
                            {/* Send Button */}
                            <button
                                onClick={handleSubmit}
                                disabled={!text.trim() || isLoading}
                                className="bg-[#023E8A] hover:bg-[#3a7bd5] text-white disabled:bg-[#023e8a]/30 w-8 h-8 rounded-full flex items-center justify-center shadow-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
                                title="Send message"
                            >
                                <ArrowUpIcon className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>

                <div className="text-[9px] text-[#5fa8ff]/40 text-center mt-2 font-bold select-none">
                    Press Shift + Enter for a new line.
                </div>
            </div>
        </div>
    );
};

/* ==========================================================================
   Role Alignment Dashboard Component
   ========================================================================== */
const ROLE_ALIGNMENT_ROLES = [
    "Transaction Banking (FX BA)",
    "Transaction Banking (Payments BA)",
    "Transaction Banking (Payments BA - Ops specialization)",
    "PaymentsOps BA",
    "Transaction Banking",
    "Accounts BA",
    "Accounts BA (US Timezone)",
    "Accounts Ops Trf BA",
    "Asset Management (French speaking BA)",
    "Lending BA",
    "UK Lending BA",
    "South Asia BA",
    "Analytics BA",
    "Analytics (Data) BA",
    "Fraud and Collections (Oak)",
    "Global Fraud BA",
    "Digital & related CCT",
    "Channels BA",
    "UK Wealth",
    "UK SME Business Banking BA",
    "UK  Generic BA",
    "Asset Management",
    "CCT - Conversation Banking",
    "Gen AI Automation BA",
];

const RoleAlignmentDashboard = () => {
    const [candidateName, setCandidateName] = useState('');
    const [resumeFile, setResumeFile] = useState(null);
    const [result, setResult] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = useRef(null);

    const getScoreColor = (score) => {
        if (score >= 80) return 'text-emerald-400';
        if (score >= 60) return 'text-yellow-400';
        return 'text-red-400';
    };

    const getScoreBg = (score) => {
        if (score >= 80) return 'bg-emerald-500/10 border-emerald-500/30';
        if (score >= 60) return 'bg-yellow-500/10 border-yellow-500/30';
        return 'bg-red-500/10 border-red-500/30';
    };

    const handleDragOver = (e) => {
        e.preventDefault();
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            const ext = file.name.split('.').pop().toLowerCase();
            if (['pdf', 'docx', 'txt'].includes(ext)) {
                setResumeFile(file);
                setError('');
            } else {
                setError('Unsupported file type. Please upload a PDF, DOCX, or TXT file.');
            }
        }
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            const ext = file.name.split('.').pop().toLowerCase();
            if (['pdf', 'docx', 'txt'].includes(ext)) {
                setResumeFile(file);
                setError('');
            } else {
                setError('Unsupported file type. Please upload a PDF, DOCX, or TXT file.');
            }
        }
    };

    const handleSubmit = async () => {
        if (!candidateName.trim()) {
            setError('Candidate name is required.');
            return;
        }
        if (!resumeFile) {
            setError('Please upload a candidate resume.');
            return;
        }
        setError('');
        setResult(null);
        setIsLoading(true);
        try {
            const formData = new FormData();
            formData.append('candidate_name', candidateName.trim());
            formData.append('file', resumeFile);

            const resp = await fetch('/api/role-alignment', {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Role alignment failed.');
            setResult(data.matches || []);
        } catch (e) {
            setError(e.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleReset = () => {
        setCandidateName('');
        setResumeFile(null);
        setResult(null);
        setError('');
    };

    return (
        <div className="flex-1 overflow-y-auto px-6 py-8 w-full animate-fade-in-up">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-3 mb-1">
                    <svg className="w-5 h-5 text-[#5fa8ff]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 9m0 8V9m0 0L9 7" />
                    </svg>
                    <h1 className="text-lg font-bold text-slate-100">Role Alignment Agent</h1>
                </div>
                <p className="text-xs text-slate-400 ml-8">Analyze an accepted candidate's profile and match them to the top 3-4 predefined Protiviti target roles.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Input Panel */}
                <div className="flex flex-col gap-4">
                    <div className="bg-[#001233] border border-[#002855] rounded-xl p-5">
                        <h2 className="text-xs font-bold text-[#5fa8ff] uppercase tracking-wider mb-4">Candidate Profile Input</h2>

                        <div className="mb-4">
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Candidate Name <span className="text-red-400">*</span></label>
                            <input
                                type="text"
                                value={candidateName}
                                onChange={e => setCandidateName(e.target.value)}
                                placeholder="e.g. Jean-Pierre Laurent"
                                className="w-full bg-[#001845] border border-[#002855] text-slate-200 text-xs rounded-lg px-3 py-2.5 outline-none focus:border-[#5fa8ff]/60 placeholder-slate-600 transition-colors"
                            />
                        </div>

                        <div className="mb-5">
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Upload Resume <span className="text-red-400">*</span></label>
                            {!resumeFile ? (
                                <div
                                    onDragOver={handleDragOver}
                                    onDrop={handleDrop}
                                    onClick={() => fileInputRef.current && fileInputRef.current.click()}
                                    className="border-2 border-dashed border-[#1e3d5f]/50 bg-[#02112a]/30 hover:border-sky-500 rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer transition-colors"
                                >
                                    <svg className="w-8 h-8 text-[#5fa8ff] mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                    <span className="text-xs text-slate-300 font-medium">Drag & drop resume here, or click to browse</span>
                                    <span className="text-[10px] text-slate-500 mt-1">Supports PDF, DOCX, TXT</span>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        accept=".pdf,.docx,.txt"
                                        onChange={handleFileChange}
                                        className="hidden"
                                    />
                                </div>
                            ) : (
                                <div className="bg-[#001845] border border-[#002855] rounded-lg p-4 flex items-center justify-between">
                                    <div className="flex items-center gap-2.5 overflow-hidden">
                                        <svg className="w-5 h-5 text-[#5fa8ff] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V7.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 1H7a2 2 0 00-2 2v16a2 2 0 002 2z" />
                                        </svg>
                                        <div className="truncate">
                                            <p className="text-xs text-slate-200 font-semibold truncate">{resumeFile.name}</p>
                                            <p className="text-[9px] text-slate-500 font-medium">{(resumeFile.size / 1024).toFixed(1)} KB</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setResumeFile(null)}
                                        className="text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-950/20 hover:bg-rose-950/40 border border-rose-900/30 rounded px-2.5 py-1.5 transition-colors cursor-pointer"
                                    >
                                        Remove
                                    </button>
                                </div>
                            )}
                        </div>

                        {error && (
                            <div className="mb-4 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2.5 text-xs text-red-400">{error}</div>
                        )}

                        <div className="flex gap-3">
                            <button
                                onClick={handleSubmit}
                                disabled={isLoading}
                                className="flex-1 bg-[#023E8A] hover:bg-[#3a7bd5] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold px-4 py-2.5 rounded-lg shadow-md transition-colors flex items-center justify-center gap-2 cursor-pointer"
                            >
                                {isLoading ? (
                                    <>
                                        <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                                        </svg>
                                        <span>Analyzing...</span>
                                    </>
                                ) : (
                                    <>
                                        <SparklesIcon className="w-3.5 h-3.5" />
                                        <span>Run Role Alignment</span>
                                    </>
                                )}
                            </button>
                            {result && (
                                <button
                                    onClick={handleReset}
                                    className="px-4 py-2.5 bg-[#001845] hover:bg-[#002855] border border-[#002855] text-slate-400 hover:text-slate-200 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                                >
                                    Reset
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Result Panel */}
                <div className="flex flex-col gap-4">
                    {!result && !isLoading && (
                        <div className="bg-[#001233] border border-[#002855] rounded-xl p-10 flex flex-col items-center justify-center text-center min-h-[260px]">
                            <svg className="w-10 h-10 text-[#002855] mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 9m0 8V9m0 0L9 7" />
                            </svg>
                            <p className="text-xs text-slate-500 max-w-xs">Upload the candidate's resume and click <strong className="text-slate-400">Run Role Alignment</strong> to get AI-powered target role matching.</p>
                        </div>
                    )}

                    {isLoading && (
                        <div className="bg-[#001233] border border-[#002855] rounded-xl p-10 flex flex-col items-center justify-center min-h-[260px]">
                            <svg className="w-8 h-8 text-[#5fa8ff] animate-spin mb-4" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                            </svg>
                            <p className="text-xs text-slate-400">AI is aligning the candidate profile against predefined target roles...</p>
                        </div>
                    )}

                    {result && result.length > 0 && (
                        <div className="flex flex-col gap-4 overflow-y-auto max-h-[600px] pr-2">
                            <h3 className="text-xs font-bold text-[#5fa8ff] uppercase tracking-wider mb-1">Target Role Alignments</h3>
                            {result.map((match, index) => (
                                <div 
                                    key={index}
                                    className={`bg-[#001233] border rounded-xl p-5 shadow-md flex flex-col gap-3 transition-colors ${getScoreBg(match.score)}`}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider mb-1">Match #{index + 1}</p>
                                            <h4 className="text-sm font-bold text-slate-100 leading-tight">{match.role}</h4>
                                        </div>
                                        <div className={`flex flex-col items-center justify-center bg-[#001845] border rounded-lg px-3 py-1.5 min-w-[64px] ${getScoreBg(match.score)}`}>
                                            <span className={`text-xl font-black ${getScoreColor(match.score)}`}>{match.score}%</span>
                                            <span className="text-[8px] text-slate-500 font-bold tracking-wide">MATCH</span>
                                        </div>
                                    </div>
                                    <div className="text-xs text-slate-300 leading-relaxed pt-2 border-t border-[#1e3d5f]/15">
                                        {match.reason}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

/* ==========================================================================
   Client Feedbacks Dashboard Component
   Compare original demand vs post-interview feedback -> categorized keywords
   ========================================================================== */
const ClientFeedbacksDashboard = () => {
    const [originalDemand, setOriginalDemand] = useState('');
    const [feedbackText, setFeedbackText] = useState('');
    const [result, setResult] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [history, setHistory] = useState([]);

    // Human-in-the-loop editable keyword state (seeded from LLM, edited by HR)
    const [editKeywords, setEditKeywords] = useState(null);
    const [newInputs, setNewInputs] = useState({ hard_skills: '', soft_skills: '', domain_knowledge: '', behavioral_knowledge: '' });
    const [isSaving, setIsSaving] = useState(false);
    const [saveMsg, setSaveMsg] = useState('');

    // Candidate & Role selectors (sourced from existing interview sessions)
    const [sessions, setSessions] = useState([]);
    const [selectedRole, setSelectedRole] = useState('');
    const [roleCandidates, setRoleCandidates] = useState([]);
    const [selectedCandidate, setSelectedCandidate] = useState('');

    const loadSessions = async () => {
        try {
            const res = await fetch('/api/sessions');
            if (res.ok) { setSessions(await res.json()); }
        } catch (e) { /* non-fatal */ }
    };

    // When a role is picked, load its candidates
    useEffect(() => {
        setSelectedCandidate('');
        setRoleCandidates([]);
        if (!selectedRole) return;
        const sess = sessions.find(s => s.role === selectedRole);
        if (!sess) return;
        (async () => {
            try {
                const res = await fetch(`/api/sessions/${sess.id}/candidates`);
                if (res.ok) { setRoleCandidates(await res.json()); }
            } catch (e) { /* non-fatal */ }
        })();
    }, [selectedRole, sessions]);

    const loadHistory = async () => {
        try {
            const res = await fetch('/api/client-feedback/history');
            if (res.ok) { const d = await res.json(); setHistory(d.feedbacks || []); }
        } catch (e) { /* non-fatal */ }
    };

    useEffect(() => { loadHistory(); loadSessions(); }, []);

    const handleAnalyze = async () => {
        if (!feedbackText.trim() || feedbackText.trim().length < 10) {
            setError('Please paste the client feedback (at least 10 characters).');
            return;
        }
        setError('');
        setResult(null);
        setEditKeywords(null);
        setSaveMsg('');
        setIsLoading(true);
        try {
            const res = await fetch('/api/client-feedback/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_demand: originalDemand.trim(),
                    raw_feedback: feedbackText.trim(),
                    similarity_threshold: 0.30,
                    save: false
                })
            });
            const data = await res.json();
            if (!res.ok) { setError(data.detail || 'Analysis failed.'); return; }
            if (data.status === 'FAILED') { setError(data.error || 'Analysis failed.'); return; }
            setResult(data);
            // Seed the editable copy from the LLM's suggestion
            const kw = data.keywords || {};
            setEditKeywords({
                hard_skills: [...(kw.hard_skills || [])],
                soft_skills: [...(kw.soft_skills || [])],
                domain_knowledge: [...(kw.domain_knowledge || [])],
                behavioral_knowledge: [...(kw.behavioral_knowledge || [])],
            });
            loadHistory();
        } catch (e) {
            setError('Server connection error. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    // --- Human-in-the-loop keyword edit helpers ---
    const removeKeyword = (cat, idx) => {
        setEditKeywords(prev => ({ ...prev, [cat]: prev[cat].filter((_, i) => i !== idx) }));
        setSaveMsg('');
    };

    const moveKeyword = (fromCat, idx, toCat) => {
        if (fromCat === toCat) return;
        setEditKeywords(prev => {
            const item = prev[fromCat][idx];
            const already = prev[toCat].some(x => x.toLowerCase() === item.toLowerCase());
            return {
                ...prev,
                [fromCat]: prev[fromCat].filter((_, i) => i !== idx),
                [toCat]: already ? prev[toCat] : [...prev[toCat], item],
            };
        });
        setSaveMsg('');
    };

    const addKeyword = (cat) => {
        const val = (newInputs[cat] || '').trim();
        if (!val) return;
        setEditKeywords(prev => {
            const already = prev[cat].some(x => x.toLowerCase() === val.toLowerCase());
            return already ? prev : { ...prev, [cat]: [...prev[cat], val] };
        });
        setNewInputs(prev => ({ ...prev, [cat]: '' }));
        setSaveMsg('');
    };

    const handleSaveReviewed = async () => {
        if (!editKeywords) return;
        const total = Object.values(editKeywords).reduce((n, arr) => n + arr.length, 0);
        if (total === 0) { setError('Add at least one keyword before saving.'); return; }
        setError('');
        setSaveMsg('');
        setIsSaving(true);
        try {
            const res = await fetch('/api/client-feedback/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_demand: originalDemand.trim(),
                    raw_feedback: feedbackText.trim(),
                    keywords: editKeywords,
                    reasoning: (result?.summary?.reasoning || '') + ' (Reviewed by HR)',
                    candidate_name: selectedCandidate,
                    role: selectedRole
                })
            });
            const data = await res.json();
            if (!res.ok) { setError(data.detail || 'Save failed.'); return; }
            setSaveMsg(`Saved ${data.saved_keyword_count} reviewed keywords (id: ${data.feedback_id}).`);
            loadHistory();
        } catch (e) {
            setError('Server connection error. Please try again.');
        } finally {
            setIsSaving(false);
        }
    };

    const CATS = [
        { key: 'hard_skills', label: 'Hard Skills', color: 'text-[#5fa8ff]', border: 'border-[#002855]', bg: 'bg-[#001233]' },
        { key: 'soft_skills', label: 'Soft Skills', color: 'text-emerald-400', border: 'border-emerald-900/40', bg: 'bg-[#0a1a0f]' },
        { key: 'domain_knowledge', label: 'Domain Knowledge', color: 'text-amber-400', border: 'border-amber-900/30', bg: 'bg-[#1a140a]' },
        { key: 'behavioral_knowledge', label: 'Behavioural Knowledge', color: 'text-pink-300', border: 'border-pink-900/30', bg: 'bg-[#1a0a14]' },
    ];

    return (
        <div className="flex-1 overflow-y-auto px-6 py-8 w-full animate-fade-in-up">
            <div className="mb-6 border-b border-[#1e3d5f]/15 pb-4">
                <h1 className="text-lg md:text-xl font-bold text-slate-100 tracking-tight">Client Feedbacks</h1>
                <p className="text-xs text-slate-400 mt-1 max-w-3xl">
                    Paste post-interview client feedback and the original demand. The system finds "out-of-the-box"
                    skills the client asked about but never listed — using cosine similarity to pre-filter, then a deep
                    LLM pass to categorize them into keywords. These keywords automatically enrich future CV screening.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
                {/* Role selector */}
                <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">Role <span className="text-slate-500 font-normal">(from interview sessions)</span></label>
                    <select
                        value={selectedRole}
                        onChange={(e) => setSelectedRole(e.target.value)}
                        className="w-full bg-[#001233] text-slate-100 border border-[#002855] rounded-xl px-3 py-2.5 text-xs outline-none focus:border-[#5fa8ff]/50 cursor-pointer"
                    >
                        <option value="">Select a role...</option>
                        {sessions.map(s => (
                            <option key={s.id} value={s.role} className="bg-[#001233] text-slate-200">{s.role}</option>
                        ))}
                    </select>
                </div>
                {/* Candidate selector */}
                <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">Candidate Name <span className="text-slate-500 font-normal">(from selected role)</span></label>
                    <select
                        value={selectedCandidate}
                        onChange={(e) => setSelectedCandidate(e.target.value)}
                        disabled={!selectedRole}
                        className="w-full bg-[#001233] text-slate-100 border border-[#002855] rounded-xl px-3 py-2.5 text-xs outline-none focus:border-[#5fa8ff]/50 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <option value="">{selectedRole ? (roleCandidates.length ? 'Select a candidate...' : 'No candidates in this role') : 'Pick a role first'}</option>
                        {roleCandidates.map(c => (
                            <option key={c.id} value={c.name || ''} className="bg-[#001233] text-slate-200">{c.name || `Candidate #${c.id}`}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
                {/* Original Demand */}
                <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">Original Demand <span className="text-slate-500 font-normal">(what was originally requested)</span></label>
                    <textarea
                        value={originalDemand}
                        onChange={(e) => setOriginalDemand(e.target.value)}
                        placeholder="Paste the original job demand / requirements here..."
                        rows={7}
                        className="w-full bg-[#001233] text-slate-100 border border-[#002855] rounded-xl p-3 text-xs outline-none focus:border-[#5fa8ff]/50 resize-none leading-relaxed"
                    />
                </div>
                {/* Client Feedback */}
                <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">Client Feedback <span className="text-red-400">*</span> <span className="text-slate-500 font-normal">(post-interview notes)</span></label>
                    <textarea
                        value={feedbackText}
                        onChange={(e) => setFeedbackText(e.target.value)}
                        placeholder="Paste the raw client feedback from the interview here. e.g. 'Client kept probing SWIFT gpi integration and FX settlement. Wanted someone who stays calm handling war-room escalations and communicates clearly with stakeholders.'"
                        rows={7}
                        className="w-full bg-[#001233] text-slate-100 border border-[#002855] rounded-xl p-3 text-xs outline-none focus:border-[#5fa8ff]/50 resize-none leading-relaxed"
                    />
                </div>
            </div>

            {error && <p className="text-xs text-rose-400 font-bold bg-rose-500/10 p-2.5 rounded-lg border border-rose-500/20 mb-4">{error}</p>}

            <div className="flex justify-end mb-8">
                <button
                    onClick={handleAnalyze}
                    disabled={isLoading}
                    className="bg-[#023e8a] hover:bg-[#0077b6] disabled:opacity-50 text-white text-xs font-bold px-6 py-2.5 rounded-lg shadow-md transition-colors flex items-center gap-2"
                >
                    {isLoading ? (
                        <>
                            <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin-custom"></div>
                            <span>Analyzing...</span>
                        </>
                    ) : (
                        <span>Analyze Feedback</span>
                    )}
                </button>
            </div>

            {/* Result — editable, human-in-the-loop review */}
            {editKeywords && (
                <div className="mb-8 animate-fade-in-up">
                    <div className="flex items-center justify-between mb-3">
                        <h2 className="text-sm font-bold text-slate-100">Review &amp; Correct Keywords</h2>
                        <span className={`text-[9px] font-bold px-2.5 py-1 rounded-full ${result?.summary?.has_new_skills ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-700 text-slate-400'}`}>
                            {result?.summary?.has_new_skills ? 'LLM SUGGESTED' : 'NO NEW SKILLS — ADD MANUALLY'}
                        </span>
                    </div>
                    {result?.summary?.reasoning && <p className="text-[11px] text-slate-400 italic mb-2">{result.summary.reasoning}</p>}
                    <div className="bg-[#001233] border border-[#5fa8ff]/20 rounded-lg p-3 mb-4">
                        <p className="text-[11px] text-[#5fa8ff] font-bold mb-1">👤 Human-in-the-loop review</p>
                        <p className="text-[10px] text-slate-400 leading-relaxed">
                            Every category below is editable. <strong className="text-slate-300">Add</strong> anything the LLM missed using the box at the bottom of each card.
                            <strong className="text-slate-300"> Move</strong> a mis-categorized skill (e.g. "project management" placed under Behavioural should go to Domain Knowledge) using the <strong className="text-slate-300">"Move to:"</strong> dropdown on each keyword.
                            <strong className="text-slate-300"> Remove</strong> a wrong keyword with ✕. Then click <strong className="text-slate-300">Save Reviewed Keywords</strong>.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {CATS.map(cat => {
                            const items = editKeywords[cat.key] || [];
                            return (
                                <div key={cat.key} className={`${cat.bg} border ${cat.border} rounded-xl p-4 flex flex-col`}>
                                    <div className={`text-[11px] font-bold ${cat.color} uppercase tracking-wider mb-3`}>{cat.label} <span className="text-slate-500">({items.length})</span></div>
                                    <div className="flex flex-col gap-2 mb-3 flex-1">
                                        {items.length === 0 ? (
                                            <p className="text-[10px] text-slate-600 italic py-1">Nothing here yet — add a keyword below.</p>
                                        ) : (
                                            items.map((item, i) => (
                                                <div key={i} className="flex items-center gap-2 bg-black/30 rounded-lg px-2.5 py-1.5">
                                                    <span className={`text-[11px] ${cat.color} font-semibold flex-1 break-words`}>{item}</span>
                                                    <select
                                                        value=""
                                                        onChange={(e) => { if (e.target.value) moveKeyword(cat.key, i, e.target.value); }}
                                                        title="Move this keyword to another category"
                                                        className="text-[9px] bg-[#0a0f1c] text-slate-300 border border-slate-700 rounded px-1.5 py-1 outline-none cursor-pointer hover:border-[#5fa8ff]/50"
                                                    >
                                                        <option value="">Move to:</option>
                                                        {CATS.filter(c => c.key !== cat.key).map(c => (
                                                            <option key={c.key} value={c.key} className="bg-[#001233] text-slate-200">{c.label}</option>
                                                        ))}
                                                    </select>
                                                    <button onClick={() => removeKeyword(cat.key, i)} title="Remove keyword" className="text-slate-500 hover:text-rose-400 text-sm font-bold leading-none px-1">✕</button>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 mt-auto pt-2 border-t border-white/5">
                                        <input
                                            type="text"
                                            value={newInputs[cat.key]}
                                            onChange={(e) => setNewInputs(prev => ({ ...prev, [cat.key]: e.target.value }))}
                                            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addKeyword(cat.key); } }}
                                            placeholder={`Add a ${cat.label.toLowerCase()} keyword...`}
                                            className="flex-1 min-w-0 bg-black/30 text-slate-200 border border-slate-800 rounded-lg px-2.5 py-1.5 text-[10px] outline-none focus:border-[#5fa8ff]/50"
                                        />
                                        <button onClick={() => addKeyword(cat.key)} className={`${cat.color} bg-black/40 hover:bg-black/60 border border-slate-700 rounded-lg px-3 py-1.5 text-[10px] font-bold`}>+ Add</button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {saveMsg && <p className="text-xs text-emerald-400 font-bold bg-emerald-500/10 p-2.5 rounded-lg border border-emerald-500/20 mt-4">{saveMsg}</p>}

                    <div className="flex justify-end mt-4">
                        <button
                            onClick={handleSaveReviewed}
                            disabled={isSaving}
                            className="bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white text-xs font-bold px-6 py-2.5 rounded-lg shadow-md transition-colors flex items-center gap-2"
                        >
                            {isSaving ? (
                                <>
                                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin-custom"></div>
                                    <span>Saving...</span>
                                </>
                            ) : (
                                <span>Save Reviewed Keywords</span>
                            )}
                        </button>
                    </div>
                </div>
            )}

            {/* History */}
            {history.length > 0 && (
                <div>
                    <h2 className="text-sm font-bold text-slate-100 mb-3 border-b border-[#1e3d5f]/15 pb-2">Feedback History ({history.length})</h2>
                    <div className="space-y-3">
                        {history.map(fb => {
                            const total = (fb.hard_skills || []).length + (fb.soft_skills || []).length + (fb.domain_knowledge || []).length + (fb.behavioral_knowledge || []).length;
                            return (
                                <div key={fb.id} className="bg-[#001233] border border-[#002855] rounded-xl p-4">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-[10px] text-slate-500 font-bold">#{fb.id} — {fb.created_at?.slice(0, 16)}</span>
                                        <span className="text-[9px] text-[#5fa8ff] font-bold bg-[#001845] px-2 py-0.5 rounded-full">{total} keywords</span>
                                    </div>
                                    {(fb.candidate_name || fb.role) && (
                                        <div className="flex flex-wrap gap-1.5 mb-2">
                                            {fb.role && <span className="text-[9px] text-amber-300 font-bold bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">{fb.role}</span>}
                                            {fb.candidate_name && <span className="text-[9px] text-emerald-300 font-bold bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">👤 {fb.candidate_name}</span>}
                                        </div>
                                    )}
                                    <p className="text-[11px] text-slate-400 line-clamp-2 mb-2 leading-relaxed">{fb.raw_feedback}</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {CATS.flatMap(cat => (fb[cat.key] || []).map((item, i) => (
                                            <span key={cat.key + i} className={`text-[9px] ${cat.color} bg-black/25 px-1.5 py-0.5 rounded font-medium`}>{item}</span>
                                        )))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

/* ==========================================================================
   Resume Standardization Tool Dashboard Component
   ========================================================================== */
const ResumeStandardizerDashboard = () => {
    const [templateFile, setTemplateFile] = useState(null);
    const [jobs, setJobs] = useState([]);
    const [jdText, setJdText] = useState("");
    const [jdMode, setJdMode] = useState("upload"); // "upload" or "text"
    const [jdFile, setJdFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState("");
    const templateInputRef = useRef(null);
    const resumesInputRef = useRef(null);
    const jdFileInputRef = useRef(null);

    const fetchJobs = async () => {
        try {
            const res = await fetch("/api/jobs");
            if (res.ok) {
                const data = await res.json();
                setJobs(data);
            }
        } catch (err) {
            console.error("Failed to load jobs list:", err);
        }
    };

    // Poll jobs queue status every 3 seconds
    useEffect(() => {
        fetchJobs();
        const interval = setInterval(fetchJobs, 3000);
        return () => clearInterval(interval);
    }, []);

    const handleTemplateUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            setTemplateFile(file);
        }
    };

    const handleJdFileUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            setJdFile(file);
            setUploadError("");
        }
    };

    const handleResumesUpload = async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        // Check if target JD is provided (either file or text)
        if (jdMode === "upload" && !jdFile) {
            setUploadError("Please upload a Job Description (JD) file first.");
            if (resumesInputRef.current) resumesInputRef.current.value = "";
            return;
        }
        if (jdMode === "text" && !jdText.trim()) {
            setUploadError("Please paste a Job Description (JD) text first.");
            if (resumesInputRef.current) resumesInputRef.current.value = "";
            return;
        }

        setIsUploading(true);
        setUploadError("");
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }
        
        if (jdMode === "upload") {
            formData.append("jd_file", jdFile);
        } else {
            formData.append("jd_text", jdText);
        }

        try {
            const res = await fetch("/api/upload-cv", {
                method: "POST",
                body: formData,
            });
            const data = await res.json();
            if (res.ok) {
                fetchJobs();
            } else {
                setUploadError(data.detail || "Failed to upload candidate resumes.");
            }
        } catch (err) {
            setUploadError("Server connection error while uploading CVs.");
        } finally {
            setIsUploading(false);
            if (resumesInputRef.current) resumesInputRef.current.value = "";
        }
    };

    const triggerDownload = (jobId, candidateName) => {
        // Direct browser file download pointing to the backend PPTX generation API
        const link = document.createElement("a");
        link.href = `/api/jobs/${jobId}/download-pptx`;
        link.setAttribute("download", "");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleDeleteJob = async (jobId) => {
        try {
            const response = await fetch(`/api/jobs/${jobId}`, {
                method: 'DELETE',
            });
            if (response.ok) {
                setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
            } else {
                const data = await response.json();
                alert(data.detail || "Failed to delete job.");
            }
        } catch (err) {
            alert("Connection error while deleting job.");
        }
    };

    // Sort queue table by match_score descending (highest first)
    const sortedJobs = [...jobs].sort((a, b) => {
        return (b.match_score || 0) - (a.match_score || 0);
    });

    return (
        <div className="flex-1 overflow-y-auto px-6 py-8 w-full animate-fade-in-up">
            <div className="mb-6 border-b border-[#1e3d5f]/15 pb-4">
                <h1 className="text-lg md:text-xl font-bold text-slate-100 tracking-tight">Resume Standardization Tool</h1>
                <p className="text-xs text-slate-400 mt-1 max-w-3xl">
                    Standardize candidate profiles against the official Protiviti styling. Upload a format reference profile template, then upload candidate CVs to start background processing.
                </p>
            </div>

            {/* Two upload dropzones */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                {/* Dropzone 1 - Standard Protiviti format resume */}
                <div 
                    onClick={() => templateInputRef.current && templateInputRef.current.click()}
                    className={`border-2 border-dashed rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors duration-200 min-h-[160px] ${
                        templateFile ? 'border-emerald-500/50 bg-[#0a1a0f]' : 'border-[#002855] hover:border-[#5fa8ff]/40 bg-[#001233]'
                    }`}
                >
                    <input 
                        type="file" 
                        ref={templateInputRef} 
                        onChange={handleTemplateUpload}
                        className="hidden" 
                        accept=".pdf,.docx,.pptx"
                    />
                    <svg className={`w-8 h-8 mb-2 ${templateFile ? 'text-emerald-400' : 'text-[#5fa8ff]'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="text-sm font-bold text-slate-100 mb-1">Upload standard protiviti format resume</h3>
                    <p className="text-[11px] text-slate-400">
                        {templateFile ? `Selected: ${templateFile.name}` : "Click or drag PDF/DOCX/PPTX standard reference template"}
                    </p>
                </div>

                {/* Dropzone 2 - Candidate resumes */}
                <div 
                    onClick={() => resumesInputRef.current && resumesInputRef.current.click()}
                    className="border-2 border-dashed border-[#002855] hover:border-[#5fa8ff]/40 rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors duration-200 bg-[#001233] min-h-[160px]"
                >
                    <input 
                        type="file" 
                        ref={resumesInputRef} 
                        onChange={handleResumesUpload}
                        className="hidden" 
                        accept=".pdf,.docx,.txt"
                        multiple
                    />
                    <svg className="w-8 h-8 text-[#5fa8ff] mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <h3 className="text-sm font-bold text-slate-100 mb-1">Upload Candidate resume/s</h3>
                    <p className="text-[11px] text-slate-400">
                        {isUploading ? "Uploading files..." : "Click or drag PDF/DOCX/TXT files (multiple allowed)"}
                    </p>
                </div>
            </div>

            {uploadError && (
                <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs p-3 rounded-lg mb-6">
                    {uploadError}
                </div>
            )}

            {/* Job Description (JD) section */}
            <div className="mb-6 bg-[#001233] border border-[#002855] rounded-xl p-5 shadow-md">
                <div className="flex justify-between items-center mb-4 border-b border-[#002855] pb-2">
                    <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">Job Description (JD)</label>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setJdMode("upload")}
                            className={`px-3 py-1 rounded-lg text-[10px] font-bold tracking-wide transition-all ${
                                jdMode === "upload" 
                                    ? "bg-[#5fa8ff] text-slate-950 shadow-md shadow-[#5fa8ff]/25" 
                                    : "bg-[#0a0f1c] text-slate-400 border border-[#002855] hover:text-slate-200"
                            }`}
                        >
                            Upload File
                        </button>
                        <button
                            onClick={() => setJdMode("text")}
                            className={`px-3 py-1 rounded-lg text-[10px] font-bold tracking-wide transition-all ${
                                jdMode === "text" 
                                    ? "bg-[#5fa8ff] text-slate-950 shadow-md shadow-[#5fa8ff]/25" 
                                    : "bg-[#0a0f1c] text-slate-400 border border-[#002855] hover:text-slate-200"
                            }`}
                        >
                            Paste Text
                        </button>
                    </div>
                </div>

                {jdMode === "upload" ? (
                    <div 
                        onClick={() => jdFileInputRef.current && jdFileInputRef.current.click()}
                        className={`border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-colors duration-200 min-h-[120px] ${
                            jdFile ? 'border-emerald-500/50 bg-[#0a1a0f]' : 'border-[#002855] hover:border-[#5fa8ff]/40 bg-[#0a0f1c]'
                        }`}
                    >
                        <input 
                            type="file" 
                            ref={jdFileInputRef} 
                            onChange={handleJdFileUpload}
                            className="hidden" 
                            accept=".pdf,.docx,.txt"
                        />
                        <svg className={`w-6 h-6 mb-2 ${jdFile ? 'text-emerald-400' : 'text-[#5fa8ff]'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <h4 className="text-xs font-bold text-slate-100 mb-1">Upload or Drag Job Description (JD)</h4>
                        <p className="text-[10px] text-slate-400">
                            {jdFile ? `Selected: ${jdFile.name}` : "Supports PDF, DOCX, TXT"}
                        </p>
                    </div>
                ) : (
                    <textarea
                        value={jdText}
                        onChange={(e) => setJdText(e.target.value)}
                        placeholder="Paste the target Job Description (JD) here to semantically align and rank candidates..."
                        rows={5}
                        className="w-full bg-[#0a0f1c] text-slate-100 border border-[#002855] rounded-lg p-3 text-xs outline-none focus:border-[#5fa8ff]/50 resize-y leading-relaxed"
                    />
                )}
            </div>

            {/* Queue section */}
            <div>
                <h2 className="text-sm font-bold text-slate-100 mb-4 border-b border-[#1e3d5f]/15 pb-2">Background Processing Queue</h2>
                {sortedJobs.length === 0 ? (
                    <div className="bg-[#001233] border border-[#002855] rounded-xl p-8 text-center text-slate-500 text-xs">
                        No standardization jobs submitted yet. Upload candidate CVs to start.
                    </div>
                ) : (
                    <div className="bg-[#001233] border border-[#002855] rounded-xl overflow-hidden shadow-lg">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-xs border-collapse">
                                <thead>
                                    <tr className="bg-[#001845]/50 text-slate-400 border-b border-[#002855] font-bold text-[10px] uppercase tracking-wider">
                                        <th className="p-3.5 pl-4">Job ID</th>
                                        <th className="p-3.5">Candidate Name</th>
                                        <th className="p-3.5">Date Submitted</th>
                                        <th className="p-3.5">Status</th>
                                        <th className="p-3.5 text-center">Match Score</th>
                                        <th className="p-3.5 pr-4 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#002855]/40 text-slate-200">
                                    {sortedJobs.map((job) => (
                                        <tr key={job.id} className="hover:bg-[#001845]/20 transition-colors">
                                            <td className="p-3.5 pl-4 font-semibold text-slate-400">#{job.id}</td>
                                            <td className="p-3.5 font-bold text-slate-100">{job.candidate_name || "Unknown"}</td>
                                            <td className="p-3.5 text-slate-400">{job.created_at?.slice(0, 16).replace('T', ' ')}</td>
                                            <td className="p-3.5">
                                                <div className="flex items-center gap-1.5">
                                                    {job.status === "PENDING" && (
                                                        <span className="flex items-center gap-1 text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded-full text-[10px]">
                                                            <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse"></span>
                                                            PENDING
                                                        </span>
                                                    )}
                                                    {job.status === "PROCESSING" && (
                                                        <span className="flex items-center gap-1 text-blue-400 font-bold bg-blue-500/10 px-2 py-0.5 rounded-full text-[10px]">
                                                            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-ping"></span>
                                                            COOKING...
                                                        </span>
                                                    )}
                                                    {job.status === "COMPLETED" && (
                                                        <span className="flex items-center gap-1 text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-full text-[10px]">
                                                            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
                                                            COMPLETED
                                                        </span>
                                                    )}
                                                    {job.status === "FAILED" && (
                                                        <span className="flex items-center gap-1 text-rose-400 font-bold bg-rose-500/10 px-2 py-0.5 rounded-full text-[10px]">
                                                            <span className="w-1.5 h-1.5 bg-rose-400 rounded-full"></span>
                                                            FAILED
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="p-3.5 text-center font-semibold">
                                                {job.status === "COMPLETED" ? (
                                                    <span 
                                                        title={job.match_reason || "Good fit"} 
                                                        className="text-xs font-bold text-sky-400 bg-sky-500/10 px-2.5 py-1 rounded-full cursor-help hover:bg-sky-500/20 transition-colors"
                                                    >
                                                        {job.match_score || 0}%
                                                    </span>
                                                ) : job.status === "FAILED" ? (
                                                    <span className="text-slate-500 italic text-[10px]">—</span>
                                                ) : (
                                                    <span className="text-slate-400 italic text-[10px] animate-pulse">Evaluating...</span>
                                                )}
                                            </td>
                                            <td className="p-3.5 pr-4 text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    {job.status === "COMPLETED" ? (
                                                        <button 
                                                            onClick={() => triggerDownload(job.id, job.candidate_name)}
                                                            className="bg-[#023E8A] hover:bg-[#3a7bd5] text-white font-bold text-[10px] px-3 py-1 rounded shadow-sm transition-colors"
                                                        >
                                                            Download
                                                        </button>
                                                    ) : (
                                                        <span className="text-[10px] text-slate-500 font-semibold italic mr-2">Processing</span>
                                                    )}
                                                    <button
                                                        onClick={() => handleDeleteJob(job.id)}
                                                        className="bg-rose-600/80 hover:bg-rose-500 text-white font-bold text-[10px] px-3 py-1 rounded shadow-sm transition-colors"
                                                    >
                                                        Delete
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

/* ==========================================================================
   ConfirmationModal Component (Custom React alert/confirm modal)
   ========================================================================== */
const ConfirmationModal = ({ isOpen, title, message, type, onConfirm, onCancel }) => {
    if (!isOpen) return null;
    return (
        <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-center justify-center animate-fade-in-up"
            onClick={onCancel}
        >
            <div 
                className="bg-[#0b192e] border border-[#1e3d5f]/30 max-w-md w-full mx-4 rounded-xl p-6 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                <h3 className="text-white text-lg font-bold mb-3">{title}</h3>
                <p className="text-slate-300 text-sm leading-relaxed mb-6">{message}</p>
                <div className="flex justify-end gap-3">
                    {type === 'confirm' && (
                        <button
                            onClick={onCancel}
                            className="px-4 py-2 rounded-lg text-sm font-semibold bg-emerald-950/40 text-emerald-400 border border-emerald-800/50 hover:bg-emerald-900/60 hover:text-emerald-200 transition-all cursor-pointer"
                        >
                            Cancel
                        </button>
                    )}
                    <button
                        onClick={onConfirm}
                        className={type === 'confirm'
                            ? "px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 text-white hover:bg-red-700 hover:shadow-lg hover:shadow-red-900/20 transition-all cursor-pointer"
                            : "px-4 py-2 rounded-lg text-sm font-semibold bg-[#023E8A] text-white hover:bg-[#3a7bd5] transition-all cursor-pointer"
                        }
                    >
                        {type === 'confirm' ? 'OK' : 'Close'}
                    </button>
                </div>
            </div>
        </div>
    );
};

/* ==========================================================================
   Main Application View (Stretches Full Screen, Oxford Blue palette globally)
   ========================================================================== */
const App = () => {
    const [activeSession, setActiveSession] = useState('new');
    const [navbarTitle, setNavbarTitle] = useState('Resume Analyzer');
    const [modalConfig, setModalConfig] = useState({ isOpen: false, title: '', message: '', type: 'alert', onConfirm: null, onCancel: null });

    const showConfirm = (title, message, onConfirm) => {
        setModalConfig({
            isOpen: true,
            title,
            message,
            type: 'confirm',
            onConfirm: () => {
                onConfirm();
                setModalConfig(prev => ({ ...prev, isOpen: false }));
            },
            onCancel: () => {
                setModalConfig(prev => ({ ...prev, isOpen: false }));
            }
        });
    };

    useEffect(() => {
        window.alert = (message) => {
            setModalConfig({
                isOpen: true,
                title: "Notification",
                message: String(message),
                type: 'alert',
                onConfirm: () => setModalConfig(prev => ({ ...prev, isOpen: false })),
                onCancel: () => setModalConfig(prev => ({ ...prev, isOpen: false }))
            });
        };
    }, []);
    const [activeJobTitle, setActiveJobTitle] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [historyList, setHistoryList] = useState([]);

    const [modalOpen, setModalOpen] = useState(false);
    const [modalContent, setModalContent] = useState('');
    const [modalTitle, setModalTitle] = useState('');

    const handleViewResume = (cvText, filename, isPdf = false) => {
        let cleanTitle = filename || "Document";
        if (isPdf) {
            if (!cleanTitle.toLowerCase().endsWith(".pdf")) {
                cleanTitle = `${cleanTitle.replace(/\s+/g, '_')}.pdf`;
            }
        }
        setModalContent(cvText);
        setModalTitle(cleanTitle);
        setModalOpen(true);
    };

    // Sessions state
    const [sessions, setSessions] = useState([
        {
            id: 'session-1',
            title: 'Resume Review - Data Scientist',
            demands: 'Senior Data Scientist with python, machine learning, and LLM fine-tuning experience.',
            response: '1. Job Title: Senior Data Scientist\n\nRole Overview:\nWe are seeking a Senior Data Scientist to spearhead LLM fine-tuning and develop robust ML pipelines.\n\nKey Responsibilities:\n- Finetune Llama models on proprietary domain text\n- Establish robust MLOps evaluation frameworks\n- Deploy real-time scalable inference APIs\n\nRequired Skills & Qualifications:\n- Expert Python, PyTorch, and HuggingFace Transformer skills\n- Solid cloud engineering experience (AWS / GCP)\n- Masters or PhD in CS/Data Science or equivalent experience'
        },
        {
            id: 'session-2',
            title: 'Cloud Architect Profile',
            demands: 'Lead Cloud Architect with expertise in Azure, Terraform, and Kubernetes.',
            response: '1. Job Title: Lead Cloud Architect\n\nRole Overview:\nWe are hiring a Lead Cloud Architect to govern our global Azure cloud environments.\n\nKey Responsibilities:\n- Author Terraform modules for multi-region Azure structures\n- Optimize enterprise-scale AKS (Kubernetes) security posture\n- Build high-availability backup systems\n\nRequired Skills & Qualifications:\n- Deep Azure, AKS, and Terraform engineering experience\n- Microsoft Solutions Architect Certification\n- 8+ years leading infrastructure designs'
        },
        {
            id: 'session-saved',
            title: 'Saved JD - Python Developer',
            demands: 'Senior Python Developer with 6+ years experience, expert in Django and cloud databases.',
            response: '1. Job Title: Senior Python Developer (Saved)\n\nRole Overview:\nThis is a saved description profile for a Senior Python Lead.\n\nKey Responsibilities:\n- Lead python development backend architecture\n- Architect robust schema designs on PostgreSQL\n- Deploy secure scalable services\n\nRequired Skills & Qualifications:\n- 6+ years experience in Python and Django\n- Experience with AWS RDS, Aurora, or PostgreSQL\n- Solid software engineering clean-code principles'
        }
    ]);

    const [messages, setMessages] = useState([]);
    const chatEndRef = useRef(null);

    // Fetch conversation history list on page load
    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await fetch('/api/history');
                if (response.ok) {
                    const data = await response.json();
                    setHistoryList(data);
                }
            } catch (err) {
                console.error("Failed to load history list:", err);
            }
        };
        fetchHistory();
    }, []);

    // Handler for selecting history list items
    const onSelectHistoryItem = async (recordId) => {
        setIsLoading(true);
        setActiveSession(recordId);
        try {
            const response = await fetch(`/api/history/${recordId}`);
            if (response.ok) {
                const result = await response.json();
                setMessages([
                    { id: 'msg-' + recordId + '-user', sender: 'user', text: result.demand },
                    { id: 'msg-' + recordId + '-bot', sender: 'bot', text: result.JD, keywords: result.keywords }
                ]);

                // Extract job title from JD
                const lines = result.JD.split('\n');
                let jobTitle = "Resume Analyzer Report";
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    if (line.toLowerCase().includes("job title:") || line.toLowerCase().startsWith("1. job title")) {
                        const parts = line.split(/:(.+)/);
                        if (parts.length > 1 && parts[1].trim()) {
                            jobTitle = parts[1].trim().replace(/\*/g, '');
                        }
                        break;
                    }
                }
                setNavbarTitle(jobTitle);
                setActiveJobTitle(jobTitle);
            } else {
                alert("Failed to load history record.");
            }
        } catch (err) {
            console.error("Error fetching history detail:", err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (activeSession === 'new') {
            setMessages([]);
            setNavbarTitle('Resume Analyzer');
            setActiveJobTitle('');
        } else if (activeSession === 'session-new-jd') {
            setMessages([]);
            setNavbarTitle('New Job Description');
            setActiveJobTitle('');
        } else if (activeSession === 'session-saved') {
            setMessages([]);
            setNavbarTitle('Saved Job Descriptions');
            setActiveJobTitle('');
        } else if (activeSession === 'session-interviews') {
            setNavbarTitle('Evaluations Complete');
        } else if (activeSession === 'session-role-alignment') {
            setMessages([]);
            setNavbarTitle('Role Alignment Agent');
            setActiveJobTitle('');
        } else if (activeSession === 'session-client-feedback') {
            setMessages([]);
            setNavbarTitle('Client Feedbacks');
            setActiveJobTitle('');
        } else if (activeSession === 'session-resume-standardizer') {
            setMessages([]);
            setNavbarTitle('Resume Standardization Tool');
            setActiveJobTitle('');
        } else if (typeof activeSession === 'string' && activeSession.startsWith('session-')) {
            const session = sessions.find(s => s.id === activeSession);
            if (session) {
                setMessages([
                    { id: session.id + '-q', sender: 'user', text: session.demands },
                    { id: session.id + '-a', sender: 'bot', text: session.response }
                ]);
                const lines = session.response.split('\n');
                let jTitle = session.title;
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    if (line.toLowerCase().includes("job title:") || line.toLowerCase().startsWith("1. job title")) {
                        const parts = line.split(/:(.+)/);
                        if (parts.length > 1 && parts[1].trim()) {
                            jTitle = parts[1].trim().replace(/\*/g, '');
                        }
                        break;
                    }
                }
                setNavbarTitle(jTitle);
                setActiveJobTitle(jTitle);
            }
        }
    }, [activeSession, sessions]);

    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isLoading]);

    const formatComparisonResult = (result) => {
        let md = `Job Title: Resume Evaluation Report\n\n`;
        md += `Overall Match Score: ${result.overall_score}/100\n\n`;

        if (result.recommendation) {
            md += `Recommendation:\n`;
            md += `- Status: **${result.recommendation.status}**\n`;
            md += `- Reasoning: ${result.recommendation.reasoning}\n\n`;
        }

        if (result.skills_analysis) {
            md += `Skills Analysis:\n`;
            md += `- Matching Skills: ${result.skills_analysis.matching_skills?.join(', ') || 'None'}\n`;
            md += `- Missing Critical Skills: ${result.skills_analysis.missing_skills?.join(', ') || 'None'}\n`;
            md += `- Optional/Nice-to-Have Skills: ${result.skills_analysis.optional_skills?.join(', ') || 'None'}\n\n`;
        }

        if (result.keyword_alignment) {
            const ratio = result.keyword_alignment.keyword_match_ratio;
            const pct = (ratio || ratio === 0) ? ` (${Math.round(ratio * 100)}% of required keywords)` : '';
            md += `Missing-Keyword Alignment${pct}:\n`;
            md += `- Keywords Matched: ${result.keyword_alignment.matched_keywords?.join(', ') || 'None'}\n`;
            md += `- Keywords Still Missing: ${result.keyword_alignment.missing_keywords?.join(', ') || 'None'}\n\n`;
        }

        if (result.experience_alignment) {
            md += `Experience Alignment:\n${result.experience_alignment}\n\n`;
        }

        if (result.strengths && result.strengths.length > 0) {
            md += `Candidate Strengths:\n`;
            result.strengths.forEach(s => {
                md += `- ✔ ${s}\n`;
            });
            md += `\n`;
        }

        if (result.gaps && result.gaps.length > 0) {
            md += `Identified Gaps:\n`;
            result.gaps.forEach(g => {
                md += `- ✘ ${g}\n`;
            });
            md += `\n`;
        }

        return md;
    };

    const handleUpload = async (files, provider, missingKeywords) => {
        if (!files || files.length === 0) return;

        for (let i = 0; i < files.length; i++) {
            if (files[i].type !== 'application/pdf' && !files[i].name.toLowerCase().endsWith('.pdf')) {
                alert(`File "${files[i].name}" is not a PDF. Only PDF files are supported.`);
                return;
            }
        }

        const botMessages = messages.filter(m => m.sender === 'bot' && !m.isError && !m.isProcessing);
        const activeJdText = botMessages.length > 0 ? botMessages[botMessages.length - 1].text : null;

        if (!activeJdText) {
            alert("Please generate a Job Description first before uploading resumes.");
            return;
        }

        setIsLoading(true);
        setNavbarTitle(`Analyzing ${files.length} Resumes...`);

        const userMsg = {
            id: 'msg-' + Date.now() + '-user',
            sender: 'user',
            text: `Uploaded ${files.length} resume(s) for evaluation (using ${provider.toUpperCase()}).`
        };
        setMessages(prev => [...prev, userMsg]);

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }
        formData.append("jd_text", activeJdText);
        formData.append("provider", provider);
        if (missingKeywords && missingKeywords.trim()) {
            formData.append("missing_keywords", missingKeywords.trim());
        }

        try {
            const response = await fetch('/api/compare-upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                result.sort((a, b) => b.overall_score - a.overall_score);

                const botMessages = result.map((evaluation, idx) => ({
                    id: 'msg-' + Date.now() + '-' + idx + '-bot',
                    sender: 'bot',
                    text: formatComparisonResult(evaluation),
                    cv_text: evaluation.cv_text,
                    filename: evaluation.filename
                }));

                setMessages(prev => [...prev, ...botMessages]);
                setNavbarTitle('Evaluations Complete');
            } else {
                const errorMsg = {
                    id: 'msg-' + Date.now() + '-bot-error',
                    sender: 'bot',
                    text: 'Error processing resume upload: ' + (result.detail || 'Unknown error'),
                    isError: true
                };
                setMessages(prev => [...prev, errorMsg]);
            }
        } catch (err) {
            const errorMsg = {
                id: 'msg-' + Date.now() + '-bot-error',
                sender: 'bot',
                text: 'Failed to connect to local FastAPI server for resume analysis.',
                isError: true
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    };


    const handleNewSession = () => {
        setActiveSession('session-new-jd');
    };

    const handleSelectSession = (id) => {
        setActiveSession(id);
    };

    const handleDeleteHistoryItem = async (recordId) => {
        try {
            const response = await fetch(`/api/client-demands/${recordId}`, {
                method: 'DELETE',
            });
            if (response.ok) {
                // Filter out the deleted item from the history list state
                setHistoryList(prev => prev.filter(item => item.id !== recordId));
                
                // If the active session is currently the deleted one, switch back to 'session-saved'
                if (activeSession === recordId) {
                    setActiveSession('session-saved');
                }
            } else {
                alert("Failed to delete the Job Description.");
            }
        } catch (err) {
            console.error("Error deleting history record:", err);
            alert("An error occurred while trying to delete the record.");
        }
    };

    const handleSaveEdit = (messageId, newText) => {
        if (!newText.trim()) return;

        const msgIndex = messages.findIndex(m => m.id === messageId);
        if (msgIndex === -1) return;

        // User demand message edited
        if (messages[msgIndex].sender === 'user') {
            // Update user demands in-place, and remove subsequent JDs (regenerating)
            const updatedMessages = messages.slice(0, msgIndex + 1);
            updatedMessages[msgIndex].text = newText;
            setMessages(updatedMessages);

            // Call the API generator with the new text to fetch new JD and wipe the previous response
            handleSend(newText, true, msgIndex);
        }
    };

    const handleSend = async (text, isRegenerate = false, editIndex = -1) => {
        setIsLoading(true);
        setNavbarTitle('New Analyzer');

        // If not regenerating, append the user message
        if (!isRegenerate) {
            const userMsg = { id: 'msg-' + Date.now() + '-user', sender: 'user', text };
            setMessages(prev => [...prev, userMsg]);
        }

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ demands: text })
            });

            const result = await response.json();

            if (response.ok) {
                const lines = result.response.split('\n');
                let jobTitle = "Resume Analyzer Report";
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    if (line.toLowerCase().includes("job title:") || line.toLowerCase().startsWith("1. job title")) {
                        const parts = line.split(/:(.+)/);
                        if (parts.length > 1 && parts[1].trim()) {
                            jobTitle = parts[1].trim().replace(/\*/g, '');
                        }
                        break;
                    }
                }

                const botMsg = {
                    id: 'msg-' + Date.now() + '-bot',
                    sender: 'bot',
                    text: result.response,
                    keywords: result.keywords,
                    matched_role: result.matched_role
                };

                if (isRegenerate && editIndex !== -1) {
                    setMessages(prev => [...prev.slice(0, editIndex + 1), botMsg]);
                } else {
                    setMessages(prev => [...prev, botMsg]);
                }

                // Update history stack state
                const newHistoryItem = {
                    id: result.id,
                    demands: text,
                    title: jobTitle,
                    created_at: new Date().toISOString()
                };

                setHistoryList(prev => {
                    const idx = prev.findIndex(item => item.id === result.id);
                    if (idx !== -1) {
                        const updated = [...prev];
                        updated[idx] = { ...updated[idx], title: jobTitle, demands: text };
                        return updated;
                    } else {
                        return [newHistoryItem, ...prev];
                    }
                });

                setActiveSession(result.id);
                setNavbarTitle(jobTitle);
                setActiveJobTitle(jobTitle);
            } else {
                const errorMsg = {
                    id: 'msg-' + Date.now() + '-bot-error',
                    sender: 'bot',
                    text: 'Error processing request: ' + (result.detail || 'Unknown error'),
                    isError: true
                };
                if (isRegenerate && editIndex !== -1) {
                    setMessages(prev => [...prev.slice(0, editIndex + 1), errorMsg]);
                } else {
                    setMessages(prev => [...prev, errorMsg]);
                }
            }
        } catch (err) {
            const errorMsg = {
                id: 'msg-' + Date.now() + '-bot-error',
                sender: 'bot',
                text: 'Failed to connect to local FastAPI server.',
                isError: true
            };
            if (isRegenerate && editIndex !== -1) {
                setMessages(prev => [...prev.slice(0, editIndex + 1), errorMsg]);
            } else {
                setMessages(prev => [...prev, errorMsg]);
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        /* Main root container spans full width in Oxford Blue (#0a0f1c) */
        <div className="w-full bg-[#0a0f1c] h-screen flex flex-row overflow-hidden relative">
            {/* Collapsible Sidebar in Oxford Blue */}
            <Sidebar
                activeSession={activeSession}
                onSelectSession={handleSelectSession}
                onNewSession={handleNewSession}
                isOpen={isSidebarOpen}
                toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                historyList={historyList}
                onSelectHistoryItem={onSelectHistoryItem}
            />

            {/* Main conversation pane (Oxford Blue bg, min-w-0 to prevent clipping) */}
            <div className="flex-1 min-w-0 flex flex-col h-full overflow-hidden bg-[#0a0f1c]">
                {/* Header bar */}
                <ChatHeader
                    title={navbarTitle}
                    toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                />

                {/* Scroll area / Dashboard */}
                <div className="flex-1 overflow-hidden relative flex flex-col justify-between">
                    {activeSession === 'session-saved' ? (
                        <SavedJDsDashboard
                            historyList={historyList}
                            onSelectHistoryItem={onSelectHistoryItem}
                            onNewSession={() => handleSelectSession('session-new-jd')}
                            onDeleteHistoryItem={handleDeleteHistoryItem}
                            onShowConfirm={showConfirm}
                        />
                    ) : activeSession === 'session-interviews' ? (
                        <InterviewSessionsDashboard />
                    ) : activeSession === 'session-role-alignment' ? (
                        <RoleAlignmentDashboard />
                    ) : activeSession === 'session-client-feedback' ? (
                        <ClientFeedbacksDashboard />
                    ) : activeSession === 'session-resume-standardizer' ? (
                        <ResumeStandardizerDashboard />
                    ) : activeSession === 'session-new-jd' ? (
                        <NewJDScreen
                            onSend={handleSend}
                            onUpload={handleUpload}
                        />
                    ) : (
                        <React.Fragment>
                            <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 flex flex-col gap-6">
                                {messages.length === 0 ? (
                                    <EmptyStateHero
                                        onSelectSession={handleSelectSession}
                                        onSend={handleSend}
                                        onUpload={handleUpload}
                                    />
                                ) : (
                                    messages.map(msg => (
                                        <ChatBubble
                                            key={msg.id}
                                            message={msg}
                                            onSaveEdit={handleSaveEdit}
                                            onViewResume={handleViewResume}
                                            jdTitle={activeJobTitle}
                                        />
                                    ))
                                )}

                                {isLoading && (
                                    <ChatBubble
                                        message={{
                                            id: 'msg-loading',
                                            sender: 'bot',
                                            text: (() => {
                                                const lastUserMsg = [...messages].reverse().find(m => m.sender === 'user');
                                                if (lastUserMsg && lastUserMsg.text.includes("Uploaded")) {
                                                    const match = lastUserMsg.text.match(/Uploaded (\d+)/);
                                                    const count = match ? match[1] : '';
                                                    return `AI is analyzing ${count} resume(s) in parallel...`;
                                                }
                                                return 'Analyzing requirements and compiling report...';
                                            })(),
                                            isProcessing: true
                                        }}
                                    />
                                )}
                                <div ref={chatEndRef} />
                            </div>

                            {/* Prompt Input Footer Bar — hidden on the landing/empty state (which has its own input) */}
                            {messages.length > 0 && (
                                <PromptInputBar
                                    key={activeSession}
                                    onSend={handleSend}
                                    onUpload={handleUpload}
                                    isLoading={isLoading}
                                    hasJd={messages.some(m => m.sender === 'bot' && !m.isError && !m.isProcessing)}
                                />
                            )}
                        </React.Fragment>
                    )}
                </div>
            </div>
            {/* Resume Modal Overlay */}
            {modalOpen && (
                <div
                    className="modal-overlay z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
                    onClick={() => setModalOpen(false)}
                >
                    <div
                        className={`modal-content-box overflow-hidden rounded-2xl shadow-2xl transition-all ${modalTitle.toLowerCase().endsWith('.pdf') ? 'bg-white max-w-5xl w-[94%] md:w-[88%]' : 'bg-[#001233] border border-[#002855] max-w-2xl'}`}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className={`px-5 py-3.5 flex justify-between items-center ${modalTitle.toLowerCase().endsWith('.pdf') ? 'bg-white border-b border-slate-200 text-slate-800' : 'bg-[#001845]/60 border-b border-[#002855] text-slate-100'}`}>
                            <h3 className="text-sm font-bold truncate flex items-center gap-2">
                                {modalTitle.toLowerCase().endsWith('.pdf') && (
                                    <svg className="w-4 h-4 text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V7.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 1H7a2 2 0 00-2 2v16a2 2 0 002 2z" />
                                    </svg>
                                )}
                                <span>{modalTitle}</span>
                            </h3>
                            <button
                                className={`p-1 rounded-lg transition-colors ${modalTitle.toLowerCase().endsWith('.pdf') ? 'text-slate-500 hover:text-slate-800 hover:bg-slate-100' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
                                onClick={() => setModalOpen(false)}
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <div className="modal-body select-text p-0">
                            {modalTitle.toLowerCase().endsWith('.pdf') ? (
                                <div className="w-full h-[680px] bg-[#323639] flex flex-col rounded-b-2xl overflow-hidden">
                                    <iframe
                                        src={`/api/resumes/pdf/${encodeURIComponent(modalTitle)}`}
                                        className="w-full h-full border-0"
                                        title={modalTitle}
                                    />
                                </div>
                            ) : typeof modalContent === 'string' && modalContent.trim().startsWith('<') ? (
                                <div dangerouslySetInnerHTML={{ __html: modalContent }} className="p-4 bg-[#13121a] text-slate-300 leading-relaxed border border-slate-800/80" />
                            ) : (
                                <div className="p-4 whitespace-pre-wrap text-slate-300 text-xs leading-relaxed">{modalContent}</div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Custom confirmation/alert dialog overlay */}
            <ConfirmationModal
                isOpen={modalConfig.isOpen}
                title={modalConfig.title}
                message={modalConfig.message}
                type={modalConfig.type}
                onConfirm={modalConfig.onConfirm}
                onCancel={modalConfig.onCancel}
            />
        </div>
    );
};

// Render React Application
const container = document.getElementById('root');
const root = ReactDOM.createRoot(container);
root.render(<App />);

import { useState, useEffect } from 'react';
import { Sidebar } from './components/sidebar/Sidebar';
import { TopNavigation } from './components/layout/TopNavigation';
import { HeroInspectionArea } from './components/inspection/HeroInspectionArea';
import { OCRResultView } from './components/ocr/OCRResultView';
import { LoginModal } from './components/auth/LoginModal';
import { CameraModal } from './components/camera/CameraModal';
import { SettingsModal } from './components/layout/SettingsModal';
import { ToastContainer } from './components/common/ToastContainer';
import { useAuth } from './hooks/useAuth';
import { useHistory } from './hooks/useHistory';
import { useInspection } from './hooks/useInspection';
import { getApiConfig } from './services/api';

export function App() {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isCameraModalOpen, setIsCameraModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);

  // Authentication hook
  const { user, login, logout, isLoading: isAuthLoading } = useAuth();

  // History hook
  const {
    historyList,
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter,
    reloadHistory,
    deleteInspection,
    renameInspection,
  } = useHistory();

  // Inspection hook
  const {
    activeRecord,
    instructionPrompt,
    setInstructionPrompt,
    selectedImages,
    pipelineStage,
    pipelineProgress,
    pipelineMessage,
    error: inspectionError,
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
    startInspection,
    loadInspection,
    resetToNew,
  } = useInspection();

  // Reload history when an inspection completes
  useEffect(() => {
    if (pipelineStage === 'complete') {
      reloadHistory();
    }
  }, [pipelineStage, reloadHistory]);

  // Pre-warm backend container silently on load to minimize cold-start delay
  useEffect(() => {
    try {
      const config = getApiConfig();
      if (config?.baseUrl) {
        fetch(`${config.baseUrl.replace(/\/+$/, '')}/`, { mode: 'cors' }).catch(() => {
          // Silent non-blocking pre-warm
        });
      }
    } catch {
      // ignore
    }
  }, []);

  const handlePhotoCaptured = (file: File) => {
    addImages([file]);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#FBFBFA] font-sans antialiased text-slate-800">
      {/* Persistent / Responsive Left Sidebar Drawer */}
      <Sidebar
        isOpenMobile={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        historyList={historyList}
        activeInspectionId={activeRecord?.id || null}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onSelectInspection={(id) => {
          loadInspection(id);
          setIsMobileSidebarOpen(false);
        }}
        onDeleteInspection={(id) => {
          deleteInspection(id);
          if (activeRecord?.id === id) {
            resetToNew();
          }
        }}
        onRenameInspection={renameInspection}
        onNewInspection={() => {
          resetToNew();
          setIsMobileSidebarOpen(false);
        }}
        onOpenSettings={() => setIsSettingsModalOpen(true)}
      />

      {/* Main Inspection View Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Navigation */}
        <TopNavigation
          onToggleSidebar={() => setIsMobileSidebarOpen(prev => !prev)}
          user={user}
          onLoginClick={() => setIsLoginModalOpen(true)}
          onLogout={logout}
          activeInspectionId={activeRecord?.id || null}
          onReloadHistory={reloadHistory}
        />

        {/* Scrollable Main Content Workspace */}
        <main className="flex-1 overflow-y-auto p-2.5 sm:p-4 md:p-6 lg:p-8 touch-pan-y">
          {activeRecord ? (
            <div className="max-w-7xl mx-auto w-full">
              <OCRResultView
                record={activeRecord}
                selectedImageIndex={activeImageIndex}
                onSelectImageIndex={setActiveImageIndex}
                selectedOcrId={selectedOcrId}
                hoveredOcrId={hoveredOcrId}
                onSelectOcrId={setSelectedOcrId}
                onHoverOcrId={setHoveredOcrId}
                showOcrBoxes={showOcrBoxes}
                onToggleShowOcrBoxes={() => setShowOcrBoxes(prev => !prev)}
                onBackToNew={resetToNew}
              />
            </div>
          ) : (
            <div className="py-1 sm:py-3 max-w-4xl mx-auto w-full">
              <HeroInspectionArea
                instructionPrompt={instructionPrompt}
                onInstructionChange={setInstructionPrompt}
                selectedImages={selectedImages}
                onFilesSelected={addImages}
                onOpenCamera={() => setIsCameraModalOpen(true)}
                onRemoveImage={removeImage}
                onSelectImageIndex={setActiveImageIndex}
                selectedImageIndex={activeImageIndex}
                onStartInspection={startInspection}
                pipelineStage={pipelineStage}
                pipelineProgress={pipelineProgress}
                pipelineMessage={pipelineMessage}
                error={inspectionError}
              />
            </div>
          )}
        </main>
      </div>

      {/* Floating Modals */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLogin={login}
        isLoading={isAuthLoading}
      />

      <CameraModal
        isOpen={isCameraModalOpen}
        onClose={() => setIsCameraModalOpen(false)}
        onPhotoCaptured={handlePhotoCaptured}
      />

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
      />

      {/* Global Toast Notifications Container */}
      <ToastContainer />
    </div>
  );
}

export default App;

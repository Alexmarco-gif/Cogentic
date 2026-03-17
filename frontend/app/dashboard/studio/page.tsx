'use client'

import { useContractStudio } from '@/lib/hooks/useContractStudio'
import { ContractStudio }    from '@/components/contracts/ContractStudio'

export default function StudioPage() {
  const {
    nlQuery,
    setNlQuery,
    schemaFields,
    addField,
    updateField,
    removeField,
    industries,
    industriesLoading,
    industriesError,
    selectedIndustryId,
    setSelectedIndustryId,
    parameters,
    updateParameter,
    step,
    isProcessing,
    access,
    runValidation,
    runSimulation,
    activateContract,
    activationError,
    resetContract,
    validationErrors,
    feasibilityData,
    syntheticPreview,
    creditEstimate,
    contracts,
    contractsLoading,
    contractActionId,
    lastCreatedContractId,
    deleteContractById,
    toggleContractActiveById,
    triggerFetchById,
    sourceDocs,
    isSourceTrayOpen,
    setIsSourceTrayOpen,
  } = useContractStudio()

  return (
    <ContractStudio
      nlQuery={nlQuery}
      onNlQueryChange={setNlQuery}
      schemaFields={schemaFields}
      onAddField={addField}
      onUpdateField={updateField}
      onRemoveField={removeField}
      industries={industries}
      industriesLoading={industriesLoading}
      industriesError={industriesError}
      selectedIndustryId={selectedIndustryId}
      onIndustryChange={setSelectedIndustryId}
      parameters={parameters}
      onUpdateParameter={updateParameter}
      step={step}
      isProcessing={isProcessing}
      access={access}
      onRunValidation={runValidation}
      onRunSimulation={runSimulation}
      onActivate={activateContract}
      activationError={activationError}
      onReset={resetContract}
      onDeleteContract={deleteContractById}
      onToggleContractActive={toggleContractActiveById}
      onTriggerContractFetch={triggerFetchById}
      validationErrors={validationErrors}
      feasibilityData={feasibilityData}
      syntheticPreview={syntheticPreview}
      creditEstimate={creditEstimate}
      contracts={contracts}
      contractsLoading={contractsLoading}
      contractActionId={contractActionId}
      lastCreatedContractId={lastCreatedContractId}
      sourceDocs={sourceDocs}
      isSourceTrayOpen={isSourceTrayOpen}
      onToggleSourceTray={() => setIsSourceTrayOpen(o => !o)}
    />
  )
}

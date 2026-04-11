interface PaystackSuccessPayload {
  reference?: string;
  trxref?: string;
  [key: string]: unknown;
}

interface PaystackResumeOptions {
  onSuccess?: (transaction: PaystackSuccessPayload) => void;
  onCancel?: () => void;
}

interface PaystackPopup {
  resumeTransaction: (
    accessCode: string,
    options?: PaystackResumeOptions,
  ) => void;
}

interface Window {
  PaystackPop?: new () => PaystackPopup;
}

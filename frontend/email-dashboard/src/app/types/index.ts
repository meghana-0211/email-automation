export interface EmailMetrics {
    total: number;
    pending: number;
    scheduled: number;
    failed: number;
    delivered: number;
    opened: number;
  }
  
  export interface EmailActivity {
    time: string;
    email: string;
    status: 'delivered' | 'failed' | 'pending';
    details: string;
  }
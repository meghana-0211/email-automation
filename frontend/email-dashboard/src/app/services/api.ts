import axios from 'axios';

// Define interfaces for type safety
interface Template {
  id?: string;
  name: string;
  content: string;
  subject: string;
}

interface CsvUploadResponse {
  columns: string[];
  preview: any[];
}

interface GoogleSheetResponse {
  columns: string[];
  preview: any[];
  total_recipients: number;
}

interface EmailJob {
  template_id: string;
  recipients: Array<{
    email: string;
    data: Record<string, any>;
  }>;
  throttle_rate?: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3000';

export const apiService = {
  // Template Management
  createTemplate: async (templateData: Template): Promise<Template> => {
    try {
      const response = await axios.post(`${API_BASE_URL}/templates`, templateData);
      return response.data;
    } catch (error) {
      console.error('Error creating template:', error);
      throw error;
    }
  },

  listTemplates: async (): Promise<Template[]> => {
    try {
      const response = await axios.get(`${API_BASE_URL}/templates`);
      return response.data;
    } catch (error) {
      console.error('Error fetching templates:', error);
      throw error;
    }
  },

  // CSV Upload
  uploadCsv: async (file: File): Promise<CsvUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(`${API_BASE_URL}/upload/csv`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      console.error('Error uploading CSV:', error);
      throw error;
    }
  },

  // Google Sheets Integration
  connectGoogleSheet: async (sheetUrl: string): Promise<GoogleSheetResponse> => {
    try {
      const response = await axios.post(`${API_BASE_URL}/google-sheets/connect`, {
        type: 'google_sheet',
        source: sheetUrl
      });
      return response.data;
    } catch (error) {
      console.error('Error connecting Google Sheet:', error);
      throw error;
    }
  },

  // Job Creation
  createEmailJob: async (jobData: EmailJob) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/jobs`, jobData);
      return response.data;
    } catch (error) {
      console.error('Error creating email job:', error);
      throw error;
    }
  },

  // Analytics
  getJobStatus: async (jobId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/jobs/${jobId}/status`);
      return response.data;
    } catch (error) {
      console.error('Error fetching job status:', error);
      throw error;
    }
  },

  getHourlyAnalytics: async (hours: number = 24) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/analytics/hourly?hours=${hours}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching hourly analytics:', error);
      throw error;
    }
  }
};
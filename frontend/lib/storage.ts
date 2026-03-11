// File upload utilities for Supabase Storage via backend API

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface UploadResponse {
  url: string;
  path: string;
}

/**
 * Upload a file to Supabase Storage via backend
 *
 * @param file - The file to upload
 * @param type - Type of asset: 'logo', 'image', or 'video'
 * @returns Public URL of the uploaded file
 */
export async function uploadFile(
  file: File,
  type: 'logo' | 'image' | 'video'
): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('type', type);

  try {
    const response = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      const errorMessage = errorData?.detail || errorData?.message || `HTTP ${response.status}`;
      throw new Error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    }

    const data: UploadResponse = await response.json();
    return data.url;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Network error - backend may be unavailable');
    }
    throw error;
  }
}

/**
 * Validate file type and size
 */
export function validateFile(
  file: File,
  type: 'logo' | 'image' | 'video'
): string | null {
  const maxSizes = {
    logo: 5 * 1024 * 1024, // 5MB
    image: 10 * 1024 * 1024, // 10MB
    video: 50 * 1024 * 1024, // 50MB
  };

  const allowedTypes = {
    logo: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'],
    image: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'],
    video: ['video/mp4', 'video/webm', 'video/quicktime'],
  };

  if (!allowedTypes[type].includes(file.type)) {
    return `Invalid file type. Allowed: ${allowedTypes[type].map(t => t.split('/')[1]).join(', ')}`;
  }

  if (file.size > maxSizes[type]) {
    const maxMB = maxSizes[type] / (1024 * 1024);
    return `File too large. Maximum size: ${maxMB}MB`;
  }

  return null;
}

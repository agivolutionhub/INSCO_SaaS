import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_URL,
});

export const getDirectories = async () => {
  const response = await api.get('/directories');
  return response.data;
};

export const getFiles = async (directory: string) => {
  const response = await api.get(`/files/${directory}`);
  return response.data;
};

export const processFile = async (inputFile: string, outputFile?: string) => {
  const response = await api.post('/process-file', { 
    input_file: inputFile,
    output_file: outputFile
  });
  return response.data;
};

export const processBatch = async (inputDir?: string, outputDir?: string) => {
  const response = await api.post('/process-batch', { 
    input_dir: inputDir,
    output_dir: outputDir
  });
  return response.data;
}; 
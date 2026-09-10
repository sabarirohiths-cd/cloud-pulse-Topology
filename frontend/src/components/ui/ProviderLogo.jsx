import React from 'react';
import { Cloud } from 'lucide-react';

export const ProviderLogo = ({ provider, verified, className = "h-5 w-auto max-w-[32px]" }) => {
  const isGrayscale = !verified;
  if (provider === 'aws') return <img src="/aws-logo.svg" alt="AWS" className={`${className} object-contain ${isGrayscale ? 'grayscale opacity-40' : ''}`} />;
  if (provider === 'azure') return <img src="/azure-logo.svg" alt="Azure" className={`${className} object-contain ${isGrayscale ? 'grayscale opacity-40' : ''}`} />;
  if (provider === 'gcp') return <img src="/gcp-logo.svg" alt="GCP" className={`${className} object-contain ${isGrayscale ? 'grayscale opacity-40' : ''}`} />;
  return <Cloud className={`h-5 w-5 ${isGrayscale ? 'text-zinc-600' : 'text-blue-400'}`} />;
};

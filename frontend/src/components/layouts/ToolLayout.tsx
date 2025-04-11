import React, { ReactNode } from 'react';
import { Helmet } from "react-helmet";

type ToolLayoutProps = {
  title: string;
  description: string;
  toolName: string;
  toolDescription: string;
  infoTitle: string;
  children: ReactNode;
  infoContent: ReactNode;
}

const ToolLayout: React.FC<ToolLayoutProps> = ({
  title,
  description,
  toolName,
  toolDescription,
  infoTitle,
  children,
  infoContent
}) => {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Helmet>
        <title>{title} | INSCO</title>
        <meta name="description" content={description} />
      </Helmet>
      
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-primary-800 mb-2">Herramienta {toolName}</h1>
        <p className="text-primary-700">
          {toolDescription}
        </p>
      </div>
      
      {children}
      
      <div className="mt-8 bg-white rounded-xl p-6 shadow-md">
        <h2 className="text-lg font-semibold text-primary-700 mb-4">{infoTitle}</h2>
        {infoContent}
      </div>
    </div>
  );
};

export default ToolLayout; 
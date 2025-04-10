import React from "react";

interface AlertProps {
  className?: string;
  children: React.ReactNode;
  variant?: "default" | "destructive";
}

export const Alert = ({ className = "", variant = "default", children }: AlertProps) => {
  const variantStyles = {
    default: "bg-blue-50 text-blue-800 border-blue-200",
    destructive: "bg-red-50 text-red-800 border-red-200"
  };

  return (
    <div
      role="alert"
      className={`relative w-full rounded-lg border p-4 ${variantStyles[variant]} ${className}`}
    >
      {children}
    </div>
  );
};

export const AlertTitle = ({ className = "", children }: { className?: string, children: React.ReactNode }) => {
  return (
    <h5
      className={`mb-1 font-medium leading-none tracking-tight ${className}`}
    >
      {children}
    </h5>
  );
};

export const AlertDescription = ({ className = "", children }: { className?: string, children: React.ReactNode }) => {
  return (
    <div
      className={`text-sm [&_p]:leading-relaxed ${className}`}
    >
      {children}
    </div>
  );
}; 
import React from "react";

interface CardProps {
  className?: string;
  children: React.ReactNode;
}

export const Card = ({ className = "", children }: CardProps) => {
  return (
    <div
      className={`rounded-lg border bg-white shadow-sm ${className}`}
    >
      {children}
    </div>
  );
};

export const CardHeader = ({ className = "", children }: CardProps) => {
  return (
    <div
      className={`flex flex-col space-y-1.5 p-6 ${className}`}
    >
      {children}
    </div>
  );
};

export const CardTitle = ({ className = "", children }: CardProps) => {
  return (
    <h3
      className={`text-lg font-semibold leading-none tracking-tight ${className}`}
    >
      {children}
    </h3>
  );
};

export const CardDescription = ({ className = "", children }: CardProps) => {
  return (
    <p
      className={`text-sm text-gray-500 ${className}`}
    >
      {children}
    </p>
  );
};

export const CardContent = ({ className = "", children }: CardProps) => {
  return (
    <div className={`p-6 pt-0 ${className}`}>
      {children}
    </div>
  );
};

export const CardFooter = ({ className = "", children }: CardProps) => {
  return (
    <div
      className={`flex items-center p-6 pt-0 ${className}`}
    >
      {children}
    </div>
  );
}; 
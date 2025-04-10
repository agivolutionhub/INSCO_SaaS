import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "destructive";
  children: React.ReactNode;
}

export const Button = ({
  variant = "default",
  children,
  className = "",
  ...props
}: ButtonProps) => {
  const baseClasses = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";
  
  const variantClasses = {
    default: "bg-gradient-to-b from-[#daaa7c] to-[#c79b6d] text-white hover:from-[#c79b6d] hover:to-[#b78c5e] shadow-md",
    outline: "border border-gray-300 bg-transparent hover:bg-gray-100 shadow-sm",
    destructive: "bg-gradient-to-b from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-md",
  };
  
  const classes = `${baseClasses} ${variantClasses[variant]} ${className}`;
  
  return (
    <button className={classes} {...props}>
      {children}
    </button>
  );
}; 
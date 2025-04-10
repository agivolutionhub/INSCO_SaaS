import React, { useEffect, useRef, useState } from "react";

interface SliderProps {
  min?: number;
  max?: number;
  step?: number;
  value?: number[];
  onValueChange?: (value: number[]) => void;
  disabled?: boolean;
  id?: string;
  className?: string;
}

export const Slider = ({
  min = 0,
  max = 100,
  step = 1,
  value = [50],
  onValueChange,
  disabled = false,
  id,
  className = "",
}: SliderProps) => {
  const [currentValue, setCurrentValue] = useState(value[0]);
  const trackRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    setCurrentValue(value[0]);
  }, [value]);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseInt(e.target.value);
    setCurrentValue(newValue);
    if (onValueChange) {
      onValueChange([newValue]);
    }
  };
  
  // Calculate percentage for styling
  const percent = ((currentValue - min) / (max - min)) * 100;
  
  return (
    <div 
      className={`relative w-full touch-none select-none ${className}`}
      id={id}
    >
      <div
        ref={trackRef}
        className="relative h-2 w-full rounded-full bg-gray-200"
      >
        <div
          className="absolute h-full rounded-full bg-primary-500"
          style={{ width: `${percent}%` }}
        />
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={currentValue}
        onChange={handleChange}
        disabled={disabled}
        className="absolute inset-0 h-2 w-full cursor-pointer appearance-none bg-transparent opacity-0"
      />
    </div>
  );
}; 
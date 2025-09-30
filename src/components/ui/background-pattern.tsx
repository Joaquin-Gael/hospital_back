import React from 'react'

export function BackgroundPattern() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden">
      {/* Animated geometric shapes */}
      <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-medical-500/10 rounded-full blur-3xl animate-float" />
      <div className="absolute top-3/4 right-1/4 w-96 h-96 bg-success-500/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '1s' }} />
      <div className="absolute bottom-1/4 left-1/3 w-80 h-80 bg-warning-500/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      
      {/* Grid pattern */}
      <svg
        className="absolute inset-0 h-full w-full opacity-20"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern
            id="grid"
            width="40"
            height="40"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="rgba(255,255,255,0.1)"
              strokeWidth="1"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {/* Medical cross pattern */}
      <div className="absolute top-10 right-10 opacity-5">
        <svg width="200" height="200" viewBox="0 0 200 200" className="text-white">
          <path
            d="M80 20 L120 20 L120 80 L180 80 L180 120 L120 120 L120 180 L80 180 L80 120 L20 120 L20 80 L80 80 Z"
            fill="currentColor"
          />
        </svg>
      </div>

      {/* DNA helix pattern */}
      <div className="absolute bottom-10 left-10 opacity-5">
        <svg width="100" height="300" viewBox="0 0 100 300" className="text-white">
          <path
            d="M20 0 Q50 25 80 50 Q50 75 20 100 Q50 125 80 150 Q50 175 20 200 Q50 225 80 250 Q50 275 20 300"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          />
          <path
            d="M80 0 Q50 25 20 50 Q50 75 80 100 Q50 125 20 150 Q50 175 80 200 Q50 225 20 250 Q50 275 80 300"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          />
        </svg>
      </div>

      {/* Pulse lines */}
      <div className="absolute top-1/2 left-0 w-full h-px bg-gradient-to-r from-transparent via-medical-400/30 to-transparent">
        <div className="w-full h-full bg-gradient-to-r from-transparent via-medical-400 to-transparent animate-pulse" />
      </div>
    </div>
  )
}
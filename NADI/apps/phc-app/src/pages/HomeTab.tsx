import { Activity, AlertTriangle, BedDouble, Stethoscope } from 'lucide-react';

export function HomeTab() {
  return (
    <div className="space-y-6">
      <div className="bg-surface rounded-xl p-6 flex flex-col items-center justify-center relative overflow-hidden border border-gray-800">
        <div className="absolute inset-0 bg-gradient-to-br from-warning/20 to-transparent"></div>
        <div className="relative z-10 text-center">
          <div 
            className="w-32 h-32 rounded-full flex items-center justify-center mx-auto mb-4 relative"
            style={{
              background: `conic-gradient(#F59E0B 60%, #1E293B 60%)`
            }}
          >
            <div className="w-[116px] h-[116px] bg-background rounded-full flex items-center justify-center absolute">
              <span className="text-3xl font-bold">60</span>
            </div>
          </div>
          <h2 className="text-xl font-bold">CBI Score</h2>
          <p className="text-warning mt-2 flex items-center justify-center font-medium">
            <AlertTriangle className="w-4 h-4 mr-1" />
            Bottleneck: Beds
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="font-semibold text-gray-300 uppercase text-sm tracking-wider">Capacity Constraints</h3>
        
        <div className="bg-surface p-4 rounded-xl border border-gray-800 space-y-2">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-success" />
              <span className="font-medium">Medicine</span>
            </div>
            <span className="text-success font-bold">82%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2">
            <div className="bg-success h-2 rounded-full" style={{ width: '82%' }}></div>
          </div>
        </div>

        <div className="bg-surface p-4 rounded-xl border border-gray-800 space-y-2">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center space-x-2">
              <BedDouble className="w-5 h-5 text-warning" />
              <span className="font-medium">Beds</span>
            </div>
            <span className="text-warning font-bold">60%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2">
            <div className="bg-warning h-2 rounded-full" style={{ width: '60%' }}></div>
          </div>
        </div>

        <div className="bg-surface p-4 rounded-xl border border-gray-800 space-y-2">
          <div className="flex justify-between items-center mb-2">
            <div className="flex items-center space-x-2">
              <Stethoscope className="w-5 h-5 text-success" />
              <span className="font-medium">Staff</span>
            </div>
            <span className="text-success font-bold">90%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2">
            <div className="bg-success h-2 rounded-full" style={{ width: '90%' }}></div>
          </div>
        </div>
      </div>
    </div>
  );
}

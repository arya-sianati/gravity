import { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import type { ActivityMetric } from '../api/activities';
import { updateMetrics } from '../api/sessions';

interface Props {
  participationId: number;
  metricsDef: ActivityMetric[];
  initialMetrics: Record<string, number> | undefined;
  onSave?: () => void;
  isFinishing?: boolean;
}

export interface MetricEntryFormHandle {
  submit: () => Promise<boolean>;
}

export const MetricEntryForm = forwardRef<MetricEntryFormHandle, Props>(({ participationId, metricsDef, initialMetrics, onSave, isFinishing }, ref) => {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialMetrics) {
      const init: Record<string, string> = {};
      Object.entries(initialMetrics).forEach(([k, v]) => {
         init[k] = String(v);
      });
      setValues(init);
    }
  }, [initialMetrics]);
  
  const handleChange = (slug: string, val: string) => {
    setValues(prev => ({ ...prev, [slug]: val }));
  };

  const handleToggle = (slug: string) => {
    setValues(prev => ({ ...prev, [slug]: prev[slug] === '1' ? '0' : '1' }));
  };

  const submit = async (): Promise<boolean> => {
    setError(null);
    const payload: Record<string, number> = {};
    for (const m of metricsDef) {
      const v = values[m.slug];
      if (v !== undefined && v !== '') {
        const parsed = Number(v);
        if (isNaN(parsed)) {
          setError(`Invalid value for ${m.name}`);
          return false;
        }
        payload[m.slug] = parsed;
      } else if (m.required) {
        setError(`${m.name} is required.`);
        return false;
      }
    }
    
    if (Object.keys(payload).length === 0) {
      return true; // Nothing to save
    }

    try {
      setSaving(true);
      await updateMetrics(participationId, payload);
      if (onSave) onSave();
      return true;
    } catch (err: any) {
      setError(err.response?.data ? JSON.stringify(err.response.data) : 'Failed to save metrics.');
      return false;
    } finally {
      setSaving(false);
    }
  };

  useImperativeHandle(ref, () => ({
    submit
  }));

  if (metricsDef.length === 0) return null;

  return (
    <div className="bg-gray-800 rounded-xl p-4 w-full max-w-sm mb-6 border border-gray-700 flex flex-col gap-3">
      <h3 className="text-gray-300 font-bold mb-1 text-sm uppercase tracking-wider">Your Metrics</h3>
      
      {metricsDef.map(m => {
        const val = values[m.slug] || '';
        if (m.data_type === 'boolean') {
          return (
             <div key={m.slug} className="flex justify-between items-center text-sm min-h-[44px]">
                <span className="text-gray-400">{m.name} {m.required ? '*' : ''}</span>
                <button 
                  onClick={() => handleToggle(m.slug)}
                  className={`w-12 h-7 rounded-full transition-colors ${val === '1' ? 'bg-indigo-600' : 'bg-gray-600'} relative p-1 active:scale-95`}
                  aria-label={`Toggle ${m.name}`}
                >
                  <span className={`block w-5 h-5 rounded-full bg-white transition-transform ${val === '1' ? 'translate-x-5' : 'translate-x-0'}`} />
                </button>
             </div>
          );
        }
        
        return (
          <div key={m.slug} className="flex justify-between items-center text-sm gap-2 min-h-[44px]">
            <label className="text-gray-400 whitespace-nowrap flex-1 text-left">{m.name} {m.required ? '*' : ''}</label>
            <div className="flex items-center gap-2">
              <input 
                type="number"
                inputMode={m.data_type === 'integer' ? 'numeric' : 'decimal'}
                step={m.data_type === 'integer' ? '1' : 'any'}
                value={val}
                onChange={e => handleChange(m.slug, e.target.value)}
                className="w-24 bg-gray-900 border border-gray-700 rounded-lg px-2.5 py-2 text-white text-right text-base focus:border-indigo-500 focus:outline-none"
                placeholder="-"
              />
              {m.unit && <span className="text-gray-400 text-xs w-8">{m.unit}</span>}
            </div>
          </div>
        );
      })}

      {error && <div className="text-red-500 text-xs mt-1">{error}</div>}
      
      {!isFinishing && (
        <button 
          onClick={submit} 
          disabled={saving}
          className="mt-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded transition-colors text-sm"
        >
          {saving ? 'Saving...' : 'Update Metrics'}
        </button>
      )}
    </div>
  );
});

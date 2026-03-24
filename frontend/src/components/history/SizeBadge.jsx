import React from 'react';
import clsx from 'clsx';

const SizeBadge = ({ size }) => {
  const styles = {
    S: 'border-blue-200 bg-blue-50 text-blue-600',
    M: 'border-emerald-200 bg-emerald-50 text-emerald-600',
    L: 'border-amber-200 bg-amber-50 text-amber-600',
    XL: 'border-violet-200 bg-violet-50 text-violet-600',
    Jumbo: 'border-red-200 bg-red-50 text-red-600',
    Unknown: 'border-slate-200 bg-slate-100 text-slate-600',
  };

  const defaultStyle = 'border-slate-200 bg-slate-100 text-slate-600';

  return (
    <span className={clsx('rounded-full border px-2.5 py-0.5 text-xs font-semibold', styles[size] || defaultStyle)}>
      {size || 'Unknown'}
    </span>
  );
};

export default SizeBadge;

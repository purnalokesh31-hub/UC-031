import { memo } from "react";

// Animated SVG of 4-qubit ZZFeatureMap — light/white theme
export default memo(function QuantumCircuitViz() {
  const qubits = [0, 1, 2, 3];
  const W = 500, H = 190;
  const yS = 28, yG = 42;
  const gates = [
    [90, 0,"H","#2e7d32"],[90,1,"H","#2e7d32"],[90,2,"H","#2e7d32"],[90,3,"H","#2e7d32"],
    [155,0,"Rz","#1d4ed8"],[155,1,"Rz","#1d4ed8"],[155,2,"Rz","#1d4ed8"],[155,3,"Rz","#1d4ed8"],
    [245,0,"ZZ","#7c3aed"],[245,1,"ZZ","#7c3aed"],[245,2,"ZZ","#7c3aed"],
    [335,0,"Rz","#1d4ed8"],[335,1,"Rz","#1d4ed8"],[335,2,"Rz","#1d4ed8"],[335,3,"Rz","#1d4ed8"],
    [420,0,"M","#b45309"],[420,1,"M","#b45309"],[420,2,"M","#b45309"],[420,3,"M","#b45309"],
  ];
  const ents = [[245,0,1],[245,1,2],[245,2,3]];

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">4-Qubit ZZFeatureMap Circuit</div>
        <div style={{ display:"flex", gap:12, marginLeft:"auto", fontSize:"0.68rem", color:"#6b7280" }}>
          {[["#2e7d32","H"],["#1d4ed8","Rz"],["#7c3aed","ZZ"],["#b45309","M"]].map(([c,l])=>(
            <span key={l} style={{ display:"flex", alignItems:"center", gap:4 }}>
              <span style={{ width:10,height:10,background:c,borderRadius:2,display:"inline-block" }}/>
              {l}
            </span>
          ))}
        </div>
      </div>
      <div className="card-body">
        <div className="circuit-wrap">
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ width:"100%" }}>
            {qubits.map(q=>(
              <g key={q}>
                <line x1={50} y1={yS+q*yG} x2={W-10} y2={yS+q*yG} stroke="#e5e7eb" strokeWidth={1.5}/>
                <text x={8} y={yS+q*yG+4} fill="#6b7280" fontSize={11} fontFamily="monospace">q{q}</text>
                <circle cx={50} cy={yS+q*yG} r={5} fill="#2e7d32" opacity={0.7}/>
              </g>
            ))}
            {ents.map(([x,q1,q2],i)=>(
              <line key={i} x1={x} y1={yS+q1*yG} x2={x} y2={yS+q2*yG} stroke="#7c3aed" strokeWidth={1.5} strokeDasharray="4 2" opacity={0.6}/>
            ))}
            {gates.map(([x,q,lbl,col],i)=>{
              const w = lbl==="Rz"?30:lbl==="ZZ"?28:22;
              return (
                <g key={i}>
                  <rect x={x-w/2} y={yS+q*yG-11} width={w} height={22} rx={4} fill={col} fillOpacity={0.12} stroke={col} strokeWidth={1.2}/>
                  <text x={x} y={yS+q*yG+4} textAnchor="middle" fill={col} fontSize={9} fontFamily="monospace" fontWeight="700">{lbl}</text>
                </g>
              );
            })}
          </svg>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginTop:12 }}>
          {[["Feature Dim","4","#2e7d32"],["Reps","2","#7c3aed"],["Entanglement","Linear","#1d4ed8"]].map(([l,v,c])=>(
            <div key={l} style={{ background:"#f8fafb", borderRadius:8, padding:"8px 10px", textAlign:"center" }}>
              <div style={{ fontSize:"1rem", fontWeight:800, color:c, fontFamily:"monospace" }}>{v}</div>
              <div style={{ fontSize:"0.65rem", color:"#9ca3af", marginTop:2 }}>{l}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

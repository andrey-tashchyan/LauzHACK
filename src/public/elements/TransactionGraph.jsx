import { useState } from 'react';

export default function TransactionGraph() {
  const transactions = props?.transactions || [];
  const [selectedNode, setSelectedNode] = useState(null);

  if (!transactions || transactions.length === 0) {
    return (
      <div style={{padding: '20px', textAlign: 'center'}}>
        No transactions to display
      </div>
    );
  }

  const nodes = new Map();
  const edgesList = [];

  transactions.forEach((txn) => {
    const source = txn.source_partner;
    const target = txn.target_partner;
    const details = txn.transaction_details;

    if (!nodes.has(source.partner_id)) {
      nodes.set(source.partner_id, {
        id: source.partner_id,
        name: source.partner_name,
        transactions: []
      });
    }
    if (!nodes.has(target.partner_id)) {
      nodes.set(target.partner_id, {
        id: target.partner_id,
        name: target.partner_name,
        transactions: []
      });
    }

    nodes.get(source.partner_id).transactions.push(txn);
    if (source.partner_id !== target.partner_id) {
      nodes.get(target.partner_id).transactions.push(txn);
    }

    const isExternal = !details.is_internal && details.ext_counterparty_account;

    edgesList.push({
      from: source.partner_id,
      to: target.partner_id,
      amount: details.amount,
      isDebit: details.debit_credit === 'debit',
      isSelfLoop: source.partner_id === target.partner_id,
      isExternal: isExternal,
      externalAccount: details.ext_counterparty_account || '',
      externalCountry: details.ext_counterparty_country || ''
    });
  });

  const nodeArray = Array.from(nodes.values());
  const width = 700;
  const height = 600;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = 220;

  nodeArray.forEach((node, i) => {
    const angle = (i / nodeArray.length) * 2 * Math.PI - Math.PI / 2;
    node.x = centerX + radius * Math.cos(angle);
    node.y = centerY + radius * Math.sin(angle);
  });

  console.log('DEBUG: Total nodes:', nodeArray.length);
  console.log('DEBUG: Total edges:', edgesList.length);
  console.log('DEBUG: First edge:', edgesList[0]);
  console.log('DEBUG: First node:', nodeArray[0]);

  return (
    <div style={{width: '100%', fontFamily: 'system-ui, -apple-system, sans-serif'}}>
      <div style={{background: 'white', borderRadius: '8px', padding: '20px', marginBottom: '20px', border: '1px solid #e5e7eb', maxWidth: '750px', margin: '0 auto 20px auto'}}>
        <h3 style={{margin: '0 0 20px 0', fontSize: '18px', fontWeight: '600'}}>Transaction Network Graph</h3>
        <svg width={width} height={height} style={{border: '1px solid #f0f0f0', borderRadius: '8px', background: '#fafafa', display: 'block', margin: '0 auto'}}>

          {edgesList.map((edge, i) => {
            const fromNode = nodeArray.find(n => n.id === edge.from);
            const toNode = nodeArray.find(n => n.id === edge.to);
            if (!fromNode || !toNode) return null;

            const edgeColor = edge.isDebit ? '#ef4444' : '#22c55e';

            if (edge.isExternal) {
              const nodeIndex = nodeArray.findIndex(n => n.id === edge.from);
              const angle = (nodeIndex / nodeArray.length) * 2 * Math.PI - Math.PI / 2;
              const externalDist = 80;
              const externalX = centerX + (radius + externalDist) * Math.cos(angle);
              const externalY = centerY + (radius + externalDist) * Math.sin(angle);

              const midX = (fromNode.x + externalX) / 2;
              const midY = (fromNode.y + externalY) / 2;

              return (
                <g key={i}>
                  <line
                    x1={externalX}
                    y1={externalY}
                    x2={fromNode.x}
                    y2={fromNode.y}
                    stroke={edgeColor}
                    strokeWidth="3"
                    strokeDasharray="5,5"
                  />
                  <circle
                    cx={externalX}
                    cy={externalY}
                    r="12"
                    fill="#f59e0b"
                    stroke="white"
                    strokeWidth="2"
                  />
                  <text
                    x={externalX}
                    y={externalY + 3}
                    fontSize="10"
                    fontWeight="700"
                    fill="white"
                    textAnchor="middle"
                  >
                    EXT
                  </text>
                  <circle
                    cx={midX}
                    cy={midY}
                    r="15"
                    fill="white"
                    stroke={edgeColor}
                    strokeWidth="2"
                  />
                  <text
                    x={midX}
                    y={midY + 4}
                    fontSize="9"
                    fontWeight="700"
                    fill={edgeColor}
                    textAnchor="middle"
                  >
                    {edge.amount >= 1000 ? (edge.amount / 1000).toFixed(1) + 'k' : edge.amount.toFixed(0)}
                  </text>
                </g>
              );
            }

            if (edge.isSelfLoop) {
              const loopSize = 40;
              const loopX = fromNode.x + loopSize;
              const loopY = fromNode.y - loopSize;

              return (
                <g key={i}>
                  <path
                    d={`M ${fromNode.x + 20} ${fromNode.y} Q ${loopX} ${loopY} ${fromNode.x} ${fromNode.y - 20}`}
                    fill="none"
                    stroke={edgeColor}
                    strokeWidth="3"
                  />
                  <circle
                    cx={loopX - 5}
                    cy={loopY}
                    r="15"
                    fill="white"
                    stroke={edgeColor}
                    strokeWidth="2"
                  />
                  <text
                    x={loopX - 5}
                    y={loopY + 4}
                    fontSize="9"
                    fontWeight="700"
                    fill={edgeColor}
                    textAnchor="middle"
                  >
                    {edge.amount >= 1000 ? (edge.amount / 1000).toFixed(1) + 'k' : edge.amount.toFixed(0)}
                  </text>
                </g>
              );
            }

            const midX = (fromNode.x + toNode.x) / 2;
            const midY = (fromNode.y + toNode.y) / 2;

            return (
              <g key={i}>
                <line
                  x1={fromNode.x}
                  y1={fromNode.y}
                  x2={toNode.x}
                  y2={toNode.y}
                  stroke={edgeColor}
                  strokeWidth="4"
                  opacity="0.8"
                />
                <circle
                  cx={midX}
                  cy={midY}
                  r="18"
                  fill="white"
                  stroke={edgeColor}
                  strokeWidth="2"
                />
                <text
                  x={midX}
                  y={midY + 4}
                  fontSize="10"
                  fontWeight="700"
                  fill={edgeColor}
                  textAnchor="middle"
                >
                  {edge.amount >= 1000 ? (edge.amount / 1000).toFixed(1) + 'k' : edge.amount.toFixed(0)}
                </text>
              </g>
            );
          })}

          {nodeArray.map((node, i) => {
            const isSelected = selectedNode === node.id;
            const nodeRadius = 30;

            return (
              <g key={i}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={nodeRadius}
                  fill={isSelected ? '#3b82f6' : '#8b5cf6'}
                  stroke="white"
                  strokeWidth="2"
                  style={{cursor: 'pointer'}}
                  onClick={() => setSelectedNode(isSelected ? null : node.id)}
                />
                <text
                  x={node.x}
                  y={node.y + 3}
                  fontSize="8"
                  fontWeight="600"
                  fill="white"
                  textAnchor="middle"
                  style={{pointerEvents: 'none'}}
                >
                  {node.name}
                </text>
              </g>
            );
          })}
        </svg>

        <div style={{marginTop: '20px', display: 'flex', gap: '15px', fontSize: '11px', color: '#6b7280', flexWrap: 'wrap'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
            <div style={{width: '25px', height: '3px', background: '#ef4444'}}></div>
            <span>Debit</span>
          </div>
          <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
            <div style={{width: '25px', height: '3px', background: '#22c55e'}}></div>
            <span>Credit</span>
          </div>
          <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
            <div style={{width: '12px', height: '12px', borderRadius: '50%', background: '#f59e0b'}}></div>
            <span>External</span>
          </div>
          <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
            <div style={{width: '12px', height: '12px', borderRadius: '50%', background: '#8b5cf6'}}></div>
            <span>Partner</span>
          </div>
        </div>
      </div>

      {selectedNode && (
        <div style={{background: 'white', borderRadius: '8px', padding: '20px', border: '1px solid #e5e7eb', maxWidth: '750px', margin: '0 auto'}}>
          <h3 style={{margin: '0 0 16px 0', fontSize: '18px', fontWeight: '600'}}>
            {nodes.get(selectedNode).name} - Transactions
          </h3>
          <div style={{maxHeight: '300px', overflowY: 'auto'}}>
            {nodes.get(selectedNode).transactions.map((txn, i) => {
              const details = txn.transaction_details;
              const isDebit = details.debit_credit === 'debit';
              const color = isDebit ? '#ef4444' : '#22c55e';

              return (
                <div key={i} style={{border: '1px solid #e5e7eb', borderRadius: '6px', padding: '12px', marginBottom: '8px'}}>
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '8px'}}>
                    <span style={{fontWeight: '600'}}>#{details.transaction_id}</span>
                    <span style={{color: color, fontWeight: '600'}}>
                      {isDebit ? '-' : '+'}{details.currency} {details.amount.toFixed(2)}
                    </span>
                  </div>
                  <div style={{fontSize: '12px', color: '#6b7280'}}>
                    {details.date} | {details.transfer_type}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

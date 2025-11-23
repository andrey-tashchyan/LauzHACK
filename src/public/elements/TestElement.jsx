export default function TestElement() {
  return (
    <div className="p-4 border rounded-md">
      <h2 className="text-lg font-bold">Test Element Working!</h2>
      <p>Props: {JSON.stringify(props)}</p>
      <p>Transactions count: {props?.transactions?.length || 0}</p>
    </div>
  );
}

"use client";

import { useState } from "react";

export default function Home() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const uploadFile = async () => {
    if (!file) {
      alert("Please select a file first");
      return;
    }

    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      console.log("Sending request to backend...");

      const res = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();

      console.log("Backend response:", result);

      if (!res.ok) {
        alert("Backend error: " + JSON.stringify(result));
        setLoading(false);
        return;
      }
      
      if (result.error) {
        alert("Backend error: " + result.error);
        setLoading(false);
        return;
      }

      setData(result);

    } catch (error) {
      console.error("Fetch error:", error);
      alert("Cannot connect to backend. Is FastAPI running?");
    }

    setLoading(false);
  };

  return (
    <div style={{ padding: "30px", fontFamily: "Arial" }}>
      <h1>💳 Smart Expense Intelligence System</h1>

      <p>
        Upload your bank statement (.csv, .xls, .xlsx)
      </p>

      <input
        type="file"
        accept=".csv,.xls,.xlsx"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <br /><br />

      <button onClick={uploadFile}>
        {loading ? "Processing..." : "Upload & Analyze"}
      </button>

      <hr />

      {data && (
        <div>
          <h2>📊 Summary</h2>
          <pre>{JSON.stringify(data.summary, null, 2)}</pre>

          <h2>💰 Total Transactions: {data.total_transactions}</h2>

          <h2>📁 Transactions</h2>

          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                {data.transactions && data.transactions.length > 0 && Object.keys(data.transactions[0]).map((key) => (
                  <th key={key} style={{ border: "1px solid #ddd", padding: "8px", textAlign: "left", textTransform: "capitalize" }}>
                    {key.replace(/_/g, " ")}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {data.transactions?.map((item, i) => (
                <tr key={i} style={{ border: "1px solid #ddd" }}>
                  {Object.keys(data.transactions[0]).map((key, j) => (
                    <td key={j} style={{ border: "1px solid #ddd", padding: "8px", maxWidth: "300px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={item[key] !== null && item[key] !== undefined ? String(item[key]) : "N/A"}>
                      {item[key] !== null && item[key] !== undefined ? String(item[key]) : "N/A"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
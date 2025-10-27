import React, { useState, useEffect } from "react";
import axios from "axios";

function FMECAAnalysis({ boardId, boardName, onBack }) {
  const [activeFilter, setActiveFilter] = useState("all");
  const [fmecaData, setFmecaData] = useState([]);
  const [atmData, setAtmData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeFilter === "atm") {
      fetchATMData();
    } else {
      fetchFMECAData();
    }
  }, [activeFilter, boardId]);

  const fetchFMECAData = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `http://localhost:8000/fmeca-data/${boardId}`,
        {
          board_id: boardId,
          filter_type: activeFilter,
        }
      );
      setFmecaData(response.data.data);
      setAtmData(null);
    } catch (error) {
      console.error("Error fetching FMECA data:", error);
      setFmecaData([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchATMData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `http://localhost:8000/atm-check/${boardId}`
      );
      setAtmData(response.data);
      setFmecaData([]);
    } catch (error) {
      console.error("Error fetching ATM data:", error);
      setAtmData(null);
    } finally {
      setLoading(false);
    }
  };

  const getRPNClass = (rpnValue) => {
    try {
      const value = parseFloat(rpnValue);
      if (value >= 70) return "rpn-high";
      if (value >= 50) return "rpn-medium";
      return "rpn-low";
    } catch {
      return "rpn-low";
    }
  };

  const getATMClass = (coverage) => {
    if (!coverage) return "status-notfound";
    if (coverage.includes("Tested") && !coverage.includes("Partially"))
      return "status-tested";
    if (coverage.includes("Partially")) return "status-partial";
    return "status-notfound";
  };

  const getATMDisplayText = (coverage) => {
    if (!coverage) return "✗ Not Found";
    if (coverage.includes("Tested") && !coverage.includes("Partially"))
      return `✓ ${coverage}`;
    if (coverage.includes("Partially")) return `⚠ ${coverage}`;
    return `✗ ${coverage}`;
  };

  const getFilterButtonClass = (filterType) => {
    return `filter-button ${
      activeFilter === filterType ? "active" : ""
    } filter-${filterType}`;
  };

  return (
    <div className="analysis-container">
      <div className="analysis-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Boards
        </button>
        <h2 className="analysis-title">{boardName} - FMECA Analysis</h2>
      </div>

      <div className="filter-buttons">
        <button
          className={getFilterButtonClass("red")}
          onClick={() => setActiveFilter("red")}
        >
          🔴 Value ≥ 70
        </button>
        <button
          className={getFilterButtonClass("orange")}
          onClick={() => setActiveFilter("orange")}
        >
          🟠 70 &gt; Value ≥ 60
        </button>
        <button
          className={getFilterButtonClass("yellow")}
          onClick={() => setActiveFilter("yellow")}
        >
          🟡 60 &gt; Value ≥ 50
        </button>
        <button
          className={getFilterButtonClass("green")}
          onClick={() => setActiveFilter("green")}
        >
          🟢 Value &lt; 50
        </button>
        <button
          className={getFilterButtonClass("atm")}
          onClick={() => setActiveFilter("atm")}
        >
          🏧 ATM Check
        </button>
        <button
          className="filter-button filter-reset"
          onClick={() => setActiveFilter("all")}
        >
          ⚫ Reset
        </button>
      </div>

      {loading && (
        <div className="loading-message">Loading data... Please wait.</div>
      )}

      {!loading && atmData && activeFilter === "atm" && (
        <>
          <div
            className={`status-message ${
              atmData.missing_components.length > 0 ? "info" : "success"
            }`}
          >
            {atmData.message}
          </div>

          {atmData.missing_components.length > 0 && (
            <div className="table-container">
              <table className="modern-table">
                <thead>
                  <tr>
                    <th>Missing Components in FMECA</th>
                    <th>ATM Coverage</th>
                  </tr>
                </thead>
                <tbody>
                  {atmData.missing_components.map((item, index) => (
                    <tr key={index}>
                      <td>{item.component}</td>
                      <td>
                        <span className={getATMClass(item.atm_coverage)}>
                          {getATMDisplayText(item.atm_coverage)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {!loading && fmecaData.length > 0 && activeFilter !== "atm" && (
        <>
          <div className="status-message info">
            Active Filter: {activeFilter.toUpperCase()} | Records Found:{" "}
            {fmecaData.length}
          </div>
          <div className="table-container">
            <table className="modern-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Component</th>
                  <th>Reference Designator</th>
                  <th>RPN</th>
                  <th>ATM Coverage</th>
                </tr>
              </thead>
              <tbody>
                {fmecaData.map((row, index) => (
                  <tr key={index}>
                    <td>{row.ID}</td>
                    <td>{row.Component}</td>
                    <td>{row.Reference_Designator}</td>
                    <td className={getRPNClass(row.RPN)}>{row.RPN}</td>
                    <td>
                      <span className={getATMClass(row.ATM_Coverage)}>
                        {getATMDisplayText(row.ATM_Coverage)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!loading && fmecaData.length === 0 && activeFilter !== "atm" && (
        <div className="status-message info">
          No data found for the selected filter.
        </div>
      )}
    </div>
  );
}

export default FMECAAnalysis;

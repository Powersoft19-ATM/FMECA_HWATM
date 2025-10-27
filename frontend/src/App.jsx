import React, { useState, useEffect } from "react";
import axios from "axios";
import MainDashboard from "./components/MainDashboard";
import FMECAAnalysis from "./components/FMECAAnalysis";
import "./App.css";

function App() {
  const [currentPage, setCurrentPage] = useState("main");
  const [selectedBoard, setSelectedBoard] = useState(null);
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBoards();
  }, []);

  const fetchBoards = async () => {
    try {
      const response = await axios.get("http://localhost:8000/boards");
      setBoards(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching boards:", error);
      setLoading(false);
    }
  };

  const handleBoardSelect = (boardId) => {
    setSelectedBoard(boardId);
    setCurrentPage("analysis");
  };

  const handleBackToBoards = () => {
    setCurrentPage("main");
    setSelectedBoard(null);
  };

  if (loading) {
    return (
      <div className="app-container">
        <div className="loading-screen">Loading...</div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {currentPage === "main" ? (
        <MainDashboard boards={boards} onBoardSelect={handleBoardSelect} />
      ) : (
        <FMECAAnalysis
          boardId={selectedBoard}
          boardName={boards.find((b) => b.id === selectedBoard)?.name}
          onBack={handleBackToBoards}
        />
      )}
    </div>
  );
}

export default App;

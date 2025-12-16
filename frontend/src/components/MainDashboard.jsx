import React from "react";

function MainDashboard({ boards, onBoardSelect }) {
  const handleBoardClick = (boardId) => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      window.location.href = "/";
      return;
    }
    onBoardSelect(boardId);
  };

  const getFileStatus = (board) => {
    if (!board.has_fmeca && !board.has_coverage) {
      return "";
    } else if (board.has_fmeca && board.has_coverage) {
      return "";
    } else {
      return "";
    }
  };

  const getStatusColor = (board) => {
    if (!board.has_fmeca && !board.has_coverage) return "";
    if (board.has_fmeca && board.has_coverage) return "#27ae60";
    return "#f39c12";
  };

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">FMECA-HWATM Integrations</h1>
      <h3 className="dashboard-subtitle">
        Select a Board to View FMECA Analysis
      </h3>
      <div className="board-grid">
        {boards.map((board) => (
          <div
            key={board.id}
            className="board-item"
            onClick={() => handleBoardClick(board.id)}
          >
            <div
              className="board-status"
              style={{ backgroundColor: getStatusColor(board) }}
            >
              {getFileStatus(board)}
            </div>
            <div
              className={`board-image ${
                board.image ? "has-image" : "no-image"
              }`}
              style={
                board.image ? { backgroundImage: `url(${board.image})` } : {}
              }
            >
              {!board.image && board.name}
            </div>
            <div className="board-name">{board.name}</div>
            <div className="board-file-info">
              {board.has_fmeca && (
                <span className="file-indicator fmeca"></span>
              )}
              {board.has_coverage && (
                <span className="file-indicator coverage"></span>
              )}
              {board.has_image && (
                <span className="file-indicator image"></span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default MainDashboard;

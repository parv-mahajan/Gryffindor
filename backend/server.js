
const express = require("express");
const cors = require("cors");
const { initializeDatabase } = require("./database");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: "1mb" }));

// Health check
app.get("/api/health", (req, res) => {
  res.json({
    success: true,
    message: "CivicSense backend is running!",
  });
});

async function startServer() {
  const { db } = await initializeDatabase();

  // GET all complaints
  app.get("/api/complaints", async (req, res) => {
    try {
      const result = await db.query(
        "SELECT * FROM complaints ORDER BY id DESC"
      );

      res.json({
        success: true,
        complaints: result.rows,
      });
    } catch (error) {
      console.error("GET complaints error:", error);
      res.status(500).json({
        success: false,
        message: "Could not retrieve complaints",
      });
    }
  });

  // POST a new complaint
  app.post("/api/complaints", async (req, res) => {
    const { title, description, category, location, priority } = req.body;

    if (
      typeof title !== "string" || !title.trim() ||
      typeof description !== "string" || !description.trim() ||
      typeof category !== "string" || !category.trim() ||
      typeof location !== "string" || !location.trim()
    ) {
      return res.status(400).json({
        success: false,
        message: "Title, description, category and location are required",
      });
    }

    const allowedPriorities = ["High", "Medium", "Low"];
    const safePriority = allowedPriorities.includes(priority)
      ? priority
      : "Medium";

    try {
      const result = await db.query(
        `INSERT INTO complaints
          (title, description, category, location, priority)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING *`,
        [
          title.trim(),
          description.trim(),
          category.trim(),
          location.trim(),
          safePriority,
        ]
      );

      res.status(201).json({
        success: true,
        complaint: result.rows[0],
      });
    } catch (error) {
      console.error("POST complaint error:", error);
      res.status(500).json({
        success: false,
        message: "Could not save complaint",
      });
    }
  });

  const server = app.listen(PORT, () => {
    console.log(`CivicSense backend listening on port ${PORT}`);
    console.log("Available endpoints:");
    console.log("GET  /api/health");
    console.log("GET  /api/complaints");
    console.log("POST /api/complaints");
  });

  server.on("error", (error) => {
    console.error("Server error:", error.message);
  });
}

startServer().catch((error) => {
  console.error("Failed to start CivicSense:", error);
  process.exitCode = 1;
});

// Helper functions for rendering analyst notes

function notesToMarkdown(notes) {
  if (typeof notes === "string") return notes;
  
  // Sky special formatting
  if (notes && notes.historical_changes && notes.current_burn_ratio) {
    let md = "### 🔥 Burn 比例历史\\n\\n";
    md += "| 日期 | 变更 | Burn 比例 |\\n";
    md += "|------|-------|----------|\\n";
    notes.historical_changes.forEach(function(change) {
      md += "| " + change.date + " | " + change.change + " | " + change.ratio + " |\\n";
    });
    md += "\\n> 📌 当前比例: **" + notes.current_burn_ratio + "** (截至 2025-10-30 执行投票)\\n\\n";
    md += "### 📊 数据源\\n\\n";
    md += "- **DefiLlama HoldersRevenue**: `buyback` | `farms` | `revenue`\\n\\n";
    md += "### 📜 合约\\n\\n";
    md += "| 合约 | 地址 |\\n";
    md += "|------|------|\\n";
    Object.keys(notes.contracts || {}).forEach(function(cName) {
      var cAddr = notes.contracts[cName];
      md += "| " + cName + " | `" + cAddr + "`|\\n";
    });
    md += "\\n### 💡 说明\\n\\n";
    md += "Splitter.burn 是链上可配置参数，通过 Executive Vote 动态调整。DefiLlama HoldersRevenue = dailyBuybackUSD + dailyStakersRevenueUSD，自动反映 burn/farm 分配结构变化。\\n";
    return md;
  }
  
  // Default for other protocols
  var md = "";
  for (var key in notes) {
    var value = notes[key];
    var label = key.replace(/_/g, " ");
    if (key === "historical_changes" && Array.isArray(value)) {
      md += "\\n### " + label + "\\n";
      value.forEach(function(change) {
        md += "- **" + change.date + "**: " + change.change + " (ratio = " + change.ratio + ") - " + change.exec_vote + "\\n";
      });
    } else if (key === "tevlama_urls" && Array.isArray(value)) {
      md += "\\n### Data Sources\\n";
      value.forEach(function(url) {
        md += "`" + url + "`\\n";
      });
    } else if (key === "contracts" && typeof value === "object") {
      md += "\\n### Contracts\\n";
      for (var cName in value) {
        md += "- **" + cName + "**: `" + value[cName] + "`\\n";
      }
    } else if (key === "note" && typeof value === "string") {
      md += "\\n> " + value + "\\n";
    } else {
      md += "- **" + label + "**: `" + value + "`\\n";
    }
  }
  return md;
}

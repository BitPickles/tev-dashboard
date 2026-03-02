// Helper functions for rendering analyst notes

function notesToMarkdown(notes) {
  if (typeof notes === "string") return notes;
  
  // Sky enhanced formatting
  if (notes && notes.overview && notes.burn_ratio) {
    const ov = notes.overview;
    const br = notes.burn_ratio;
    
    let md = `### 📊 概览\n\n`;
    md += `| 指标 | 值 |\n`;
    md += `|------|-----|\n`;
    md += `| 最近 12 个月 TEV | ${ov.tev_12m} |\n`;
    md += `| 最新月度 TEV | ${ov.latest_month} |\n`;
    md += `| 机制 | ${ov.mechanism} |\n`;
    md += `| 收益来源 | ${ov.yield_source} |\n`;
    
    md += `\n### 🔥 Burn 比例\n\n`;
    md += `> 当前比例: **${br.current}** (${br.current * 100}%) · 通过 **${br.governance}** 调整\n\n`;
    md += `| 日期 | 变更 | Burn 比例 |\n`;
    md += `|------|-------|----------|\n`;
    notes.historical_changes.forEach(c => {
      md += `| ${c.date} | ${(c.from * 100).toFixed(0)}% → ${(c.to * 100).toFixed(0)}% | ${c.to} |\n`;
    });
    
    md += `\n### 📜 合约\n\n`;
    md += `| 合约 | 地址 |\n`;
    md += `|------|------|\n`;
    Object.entries(notes.contracts).forEach(([name, addr]) => {
      md += `| ${name} | \`${addr}\` |\n`;
    });
    
    md += `\n### 🔗 相关链接\n\n`;
    md += `- [治理投票](${notes.links.governance}) - Sky Executive Vote\n`;
    md += `- [Burn Engine](${notes.links.burn_engine}) - BlockAnalitica\n`;
    md += `- [API](${notes.links.api}) - DefiLlama HoldersRevenue\n`;
    
    md += `\n### 💡 机制说明\n\n`;
    md += notes.mechanism_note + `\n`;
    
    md += `\n### 📊 数据源\n\n`;
    md += `DefiLlama **HoldersRevenue** = buyback + stakers_reward，自动反映治理投票后的分配比例变化。\n`;
    
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

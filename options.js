// options.js
document.addEventListener("DOMContentLoaded", async () => {
  const r = await chrome.runtime.sendMessage({ action: "getSettings" });
  if (r) {
    document.getElementById("llmProvider").value = r.llm?.provider || "openai";
    document.getElementById("llmApiKey").value = r.llm?.apiKey || "";
    document.getElementById("llmModel").value = r.llm?.model || "gpt-4o-mini";
    document.getElementById("ccfAutoFetch").checked = r.ccfAutoFetch !== false;
    document.querySelectorAll("#arxivCats input").forEach(cb => {
      cb.checked = (r.arxivCategories || []).includes(cb.value);
    });
  }

  document.getElementById("btnSaveSettings").addEventListener("click", async () => {
    const settings = {
      llm: {
        provider: document.getElementById("llmProvider").value,
        apiKey: document.getElementById("llmApiKey").value,
        model: document.getElementById("llmModel").value
      },
      arxivCategories: [...document.querySelectorAll("#arxivCats input:checked")].map(cb => cb.value),
      ccfAutoFetch: document.getElementById("ccfAutoFetch").checked
    };
    await chrome.runtime.sendMessage({ action: "saveSettings", settings });
    alert("设置已保存");
  });

  document.getElementById("btnTestLLM").addEventListener("click", async () => {
    // 简单测试：调用LLM分类一个示例
    const provider = document.getElementById("llmProvider").value;
    const apiKey = document.getElementById("llmApiKey").value;
    const model = document.getElementById("llmModel").value;
    if (provider !== "ollama" && !apiKey) { alert("请先填写 API Key"); return; }
    try {
      const client = new LLMClient({ provider, apiKey, model });
      const result = await client.classifyPaper("Test Paper", "A test abstract about security.");
      alert("连接成功！\n" + JSON.stringify(result, null, 2));
    } catch (e) {
      alert("连接失败：" + e.message);
    }
  });
});

# LangSmith starter notes

LangSmith is the observability layer in this demo. A trace records what ran
for one question, including the outer LangGraph workflow and the nested
Deep Agent model and tool calls. Inspect inputs, outputs, duration, and
reported token usage to connect the code with its actual execution.

LangGraph controls the outer sequence, Deep Agents manages the inner agent
loop, and LangSmith records their execution. A trace shows actual tool calls;
having a tool available does not guarantee that the model will call it.

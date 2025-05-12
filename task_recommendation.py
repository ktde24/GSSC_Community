import streamlit as st
import logging
from openai_utils import get_chat_response
import pandas as pd

logging.basicConfig(level=logging.INFO)

def build_task_prompt(task_list, team_traits):
    tasks_str = "\n".join(f"{i+1}. {task.strip()}" for i, task in enumerate(task_list))
    return f"""
You are an AI assistant tasked with assigning responsibilities based on each team member’s traits.

[Team Member Traits]
{team_traits}

[Task List]
{tasks_str}

- Give the entire task assignment result in english.
- Do not use gendered pronouns such as "he" or "she." Use the person's name instead in the justification.
- Assign exactly one team member to each task, along with a brief justification.
- Your justification must reflect the individual’s actual traits.
- Do not assign tasks based on traits the person does not have (e.g., do not cite creativity for someone who is not described as creative).
- Use proper language to describe trait levels (e.g., “moderate,” “high,” etc.).
- If the number of tasks is fewer than the number of team members, create additional tasks as needed. 
  If there are more tasks than members, merge simple or similar tasks so that each task is assigned to one person.

- Respond using only the markdown table format shown below.
| Task | Assigned Member | Reason for Assignment |
|------|------------------|------------------------|
| Sample Task | Sample Member | Write the reason for assignment here |
"""

def parse_markdown_table(md_table):
    lines = [line for line in md_table.split('\n') if '|' in line]
    if len(lines) < 2:
        return None
    headers = [h.strip() for h in lines[0].split('|')[1:-1]]
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) == len(headers):
            rows.append(cells)
    if rows:
        return pd.DataFrame(rows, columns=headers)
    return None

def task_recommendation_ui():
    st.title("📝 Automated Task Assignment")
    
    # 입력 필드 
    team_traits = st.text_area("Enter team member traits (use the example format)", 
                             placeholder="ex:\nAmy: Intuitive, creative")
    
    task_list = st.text_area("Enter the list of tasks (one per line)", 
                           placeholder="ex:\nMarket research analysis\nPrototype development")

    if st.button("Assign Tasks"):
        if not team_traits.strip() or not task_list.strip():
            st.error("Please enter both team member traits and the task list.")
            return

        try:
            processed_tasks = [t.strip() for t in task_list.split('\n') if t.strip()]
            
            with st.spinner("AI is analyzing the optimal task assignment..."):
                prompt = build_task_prompt(processed_tasks, team_traits)
                response = get_chat_response([{"role": "user", "content": prompt}])
                
            st.success("✅ Task assignment completed!")
            st.markdown("""
            <div style="margin-bottom:1em; font-size:1.1rem;">
                👋 The table below shows the result of assigning the most suitable tasks to each team member.
            </div>
            """, unsafe_allow_html=True)
            
            df = parse_markdown_table(response)
            if df is not None:
                st.dataframe(df, hide_index=True, use_container_width=True)
                # 팀원별 요약 메시지는 expander로 감추기
                with st.expander("Detail"):
                    for idx, row in df.iterrows():
                        st.info(f"**{row['Assigned Member']}** has been assigned the task '**{row['Task']}**'.\n\n> {row['Reason for Assignment']}")

            else:
                st.markdown(response)
                        
        except Exception as e:
            logging.error(f"Error: {str(e)}")
            st.error("처리 중 오류가 발생했습니다. 입력 형식을 확인해 주세요.")

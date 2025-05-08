import streamlit as st
import logging
from openai_utils import get_chat_response
import pandas as pd

logging.basicConfig(level=logging.INFO)

def build_task_prompt(task_list, team_traits):
    tasks_str = "\n".join(f"{i+1}. {task.strip()}" for i, task in enumerate(task_list))
    return f"""
당신은 팀원 성향을 고려해 업무를 적절히 배분하는 AI입니다.

[팀원 성향]
{team_traits}

[해야 할 일 목록]
{tasks_str}

- 각 업무에 대해 적합한 팀원 1명을 배정하고, 그 이유도 간단히 설명하세요.
- 설명에 포함되는 역량은 해당 인물의 실제 성향과 일치해야 합니다.
- 표현은 구체적으로 작성하세요. (예: '중간', '높음' 등 성향 수준 반영)
- 아래와 같은 마크다운 표 형식으로만 답변하세요.
| 업무 | 배정 팀원 | 배정 이유 |
|------|-----------|-----------|
| 예시 업무 | 예시 팀원 | 예시 이유를 여기에 작성 |
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
                👋 아래 표는 팀원별로 가장 적합한 업무를 배정한 결과입니다.
            </div>
            """, unsafe_allow_html=True)
            
            df = parse_markdown_table(response)
            if df is not None:
                st.dataframe(df, hide_index=True, use_container_width=True)
                # 팀원별 요약 메시지는 expander로 감추기
                with st.expander("자세히 보기"):
                    for idx, row in df.iterrows():
                        st.info(f"**{row['배정 팀원']}**님은 **'{row['업무']}'** 업무를 맡게 되었어요!\n\n> {row['배정 이유']}")
            else:
                st.markdown(response)
                        
        except Exception as e:
            logging.error(f"Error: {str(e)}")
            st.error("처리 중 오류가 발생했습니다. 입력 형식을 확인해 주세요.")

# keyboard_nav.py
"""
نظام التنقل الذكي باستخدام مفتاح Enter
محدث لتجنب المشاكل مع حقول password
"""

import streamlit as st
import streamlit.components.v1 as components

def enable_enter_navigation(form_key=None):
    """
    تفعيل التنقل بمفتاح Enter
    مع تعطيله في حقول password لتجنب المشاكل
    """
    
    javascript_code = f"""
    <script>
    (function() {{
        setTimeout(function() {{
            // العثور على جميع حقول الإدخال (ما عدا password)
            const inputs = document.querySelectorAll(
                'input[type="text"], input[type="number"], input[type="email"], textarea'
            );
            
            inputs.forEach(function(input, index) {{
                input.addEventListener('keydown', function(event) {{
                    if (event.key === 'Enter') {{
                        // السماح بـ Shift+Enter في textarea
                        if (event.shiftKey && this.tagName === 'TEXTAREA') {{
                            return;
                        }}
                        
                        event.preventDefault();
                        
                        // الانتقال للحقل التالي
                        if (index < inputs.length - 1) {{
                            inputs[index + 1].focus();
                            inputs[index + 1].select();
                        }}
                    }}
                }});
            }});
        }}, 500);
    }})();
    </script>
    """
    
    components.html(javascript_code, height=0, width=0)


def add_enter_hint():
    """إضافة تلميح للمستخدم"""
    st.markdown("""
    <style>
        .enter-hint {
            position: fixed;
            bottom: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 12px;
            z-index: 9999;
        }
    </style>
    <div class="enter-hint">
        💡 اضغط <b>Enter</b> للانتقال بين الحقول
    </div>
    """, unsafe_allow_html=True)
import streamlit as st
import database as db
import pandas as pd
from datetime import datetime

def show():
    st.title("📄 reports")
    st.info("هذه الصفحة جاهزة وتتصل بقاعدة البيانات. سيتم تطوير محتواها لاحقاً.")
    try:
        _, rows = db.execute_query("SELECT table_name FROM information_schema.tables WHERE table_schema='public' LIMIT 5", fetch=True)
        st.write("اختبار الاتصال بقاعدة البيانات: نجح!")
    except Exception as e:
        st.error(f"خطأ: {e}")
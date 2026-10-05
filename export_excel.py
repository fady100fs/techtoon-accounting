def export_balance_sheet_to_excel(
    assets_data: list,
    liabilities_data: list,
    equity_data: list,
    total_assets: float,
    total_liabilities: float,
    total_equity: float,
    net_profit: float,
    output_path: str = None
):
    """
    تصدير الميزانية العمومية إلى Excel
    """
    from datetime import datetime
    
    if not output_path:
        output_path = f"Balance_Sheet_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # تنسيق العنوان
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'bg_color': '#1F4E78',
            'font_color': 'white'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1,
            'font_size': 12
        })
        
        # الأصول
        assets_df = pd.DataFrame(assets_data)
        assets_df.to_excel(writer, sheet_name='الأصول', index=False, startrow=2)
        worksheet_assets = writer.sheets['الأصول']
        worksheet_assets.write(0, 0, "الأصول (Assets)", title_format)
        
        for i in range(len(assets_df.columns)):
            worksheet_assets.set_column(i, i, 20)
        
        worksheet_assets.write(len(assets_df) + 3, 0, "إجمالي الأصول:", total_format)
        worksheet_assets.write(len(assets_df) + 3, 3, total_assets, total_format)
        
        # الخصوم
        liabilities_df = pd.DataFrame(liabilities_data)
        liabilities_df.to_excel(writer, sheet_name='الخصوم', index=False, startrow=2)
        worksheet_liabilities = writer.sheets['الخصوم']
        worksheet_liabilities.write(0, 0, "الخصوم (Liabilities)", title_format)
        
        for i in range(len(liabilities_df.columns)):
            worksheet_liabilities.set_column(i, i, 20)
        
        worksheet_liabilities.write(len(liabilities_df) + 3, 0, "إجمالي الخصوم:", total_format)
        worksheet_liabilities.write(len(liabilities_df) + 3, 3, total_liabilities, total_format)
        
        # حقوق الملكية
        equity_df = pd.DataFrame(equity_data)
        equity_df.to_excel(writer, sheet_name='حقوق الملكية', index=False, startrow=2)
        worksheet_equity = writer.sheets['حقوق الملكية']
        worksheet_equity.write(0, 0, "حقوق الملكية (Equity)", title_format)
        
        for i in range(len(equity_df.columns)):
            worksheet_equity.set_column(i, i, 20)
        
        worksheet_equity.write(len(equity_df) + 3, 0, "إجمالي حقوق الملكية:", total_format)
        worksheet_equity.write(len(equity_df) + 3, 3, total_equity, total_format)
        
        # ملخص
        summary_df = pd.DataFrame({
            'البند': ['إجمالي الأصول', 'إجمالي الخصوم', 'إجمالي حقوق الملكية', 'صافي الربح/الخسارة', 'الخصوم + حقوق الملكية'],
            'المبلغ': [total_assets, total_liabilities, total_equity, net_profit, total_liabilities + total_equity]
        })
        summary_df.to_excel(writer, sheet_name='الملخص', index=False, startrow=2)
        worksheet_summary = writer.sheets['الملخص']
        worksheet_summary.write(0, 0, "ملخص الميزانية العمومية", title_format)
        
        for i in range(len(summary_df.columns)):
            worksheet_summary.set_column(i, i, 25)
    
    print(f"✅ تم تصدير الميزانية العمومية إلى: {output_path}")
    return output_path
def sales_analysis(r, q):
    sa = f"""
        SELECT
            s.CUSTOMER, s.ITEM, i.FMTITEMNO, i.[DESC], s.YR, s.PERIOD, s.TRANDATE,
            s.TRANNUM, s.ORDNUMBER, s.SALESPER, s.LOCATION, s.TERRITORY,
            s.CATEGORY, c.[DESC], s.SCURN, s.FAMTSALES, s.FRETSALES,
            s.FCSTSALES, (s.FAMTSALES-s.FRETSALES) AS NETSALES
        FROM OESHDT s
        JOIN ICITEM i ON i.ITEMNO = s.ITEM
        JOIN ICCATG c ON c.CATEGORY = s.CATEGORY
        WHERE {r} = '{q}'
    """
    return sa

def inv_analysis(q):
    sa = f"""
        SELECT
            RTRIM(s.CUSTOMER) AS 'Customer',
            RTRIM(i.FMTITEMNO) AS 'Item',
            RTRIM(i.[DESC]) AS 'Description',
            CAST(s.YR AS varchar) AS 'Year',
            CAST(s.PERIOD AS varchar) AS 'Period',
            CONVERT(datetime,CONVERT(char(8),s.TRANDATE)) AS 'Trandate',
            RTRIM(s.LOCATION) AS 'Location',
            SUM(s.QTYSOLD) AS 'Quantity',
            SUM(l.TOTALCOST) AS 'TotalCost',
            SUM(FAMTSALES-FRETSALES) AS 'Netsales',
            (l.QTYONHAND-l.QTYCOMMIT) AS 'QtyAV',
            l.QTYSALORDR AS 'QtySO',
            l.QTYONORDER AS 'QtyPO'
        FROM OESHDT s
        JOIN ICILOC l ON l.ITEMNO = s.ITEM AND l.[LOCATION] = s.[LOCATION]
        JOIN ICITEM i ON l.ITEMNO = i.ITEMNO
        WHERE i.FMTITEMNO = '{q}'
        GROUP BY s.CUSTOMER, i.FMTITEMNO, i.[DESC], s.YR, s.PERIOD,
            s.TRANDATE, s.LOCATION, l.QTYONHAND, l.QTYCOMMIT,
            l.QTYSALORDR, l.QTYONORDER
    """
    return sa

UNPAID_RECEIVABLES = """
    SELECT
    CASE
        WHEN d .[TRXTYPETXT] = 1 THEN 'Invoice'
        WHEN d .[TRXTYPETXT] = 2 THEN 'Debit Note'
        WHEN d .[TRXTYPETXT] = 3 THEN 'Credit Note'
        WHEN d .[TRXTYPETXT] = 4 THEN 'Interest'
        WHEN d .[TRXTYPETXT] = 5 THEN 'Unapplied Cash'
        WHEN d .[TRXTYPETXT] = 10 THEN 'Prepayment'
        WHEN d .[TRXTYPETXT] = 11 THEN 'Receipt'
        WHEN d .[TRXTYPETXT] = 19 THEN 'Refund'
        ELSE 'Unknown'
    END AS DOCTYPE,
    d.IDCUST, NAMECUST, IDINVC, IDORDERNBR, d.IDGRP, DATEINVC, DATEDUE, DATEASOF,
    d.CODESLSP1, d.CODESLSP2, d.CODESLSP3, d.CODESLSP4, d.CODESLSP5 IDSHIPNBR, d.CODETERR, CODECTRY,
    DATELSTACT, DATELSTSTM, d.CODETERM, d.CODECURN, AMTINVCHC, AMTDUEHC, ISNULL
    (
        (
            SELECT TOP(1) AMTDUEHC
            FROM ARRTB AS t
            WHERE DATEDIFF(DAY, (CONVERT(DATE, NULLIF (CONVERT(VARCHAR(8), CONVERT(INT, d.DATEDUE)), 0))), CONVERT(DATE, GETDATE(),0) ) > t.DUEDAYS
            GROUP BY DUEDAYS
            ORDER BY DUEDAYS DESC
        ), 0
    ) AS INAMTOVER, ISNULL
    (
        (
            SELECT TOP (1) SUM(PCTDUE) AS Expr1
            FROM dbo.ARRTB AS t
            WHERE (CODETERM = d.CODETERM) AND (DATEADD(DAY, DUEDAYS, CONVERT(DATE, NULLIF (CONVERT(VARCHAR(10), CONVERT(INT, d.DATEINVC)), 0))) < GETDATE())
            GROUP BY CODETERM
        ), 0
    ) AS TERMPERTOVER, ISNULL
    (
        (
            SELECT TOP (1)
            CASE
                WHEN DATEDIFF(DAY, (CONVERT(DATE, NULLIF (CONVERT(VARCHAR(8), CONVERT(INT, d.DATEDUE)), 0))), CONVERT(DATE, GETDATE(),0)) < 0
                THEN DATEDIFF(DAY, (CONVERT(DATE, NULLIF (CONVERT(VARCHAR(8), CONVERT(INT, d.DATEDUE)), 0))), CONVERT(DATE, GETDATE(),0)) * -1
            ELSE
                DATEDIFF(DAY, (CONVERT(DATE, NULLIF (CONVERT(VARCHAR(8), CONVERT(INT, d.DATEDUE)), 0))), CONVERT(DATE, GETDATE(),0))
            END
            FROM dbo.ARRTB AS t
            WHERE (CODETERM = d.CODETERM)
            ORDER BY CODETERM, CNTPAYM
        ), 0
    ) AS TERMDAYSOVER

    FROM dbo.AROBL AS d
    JOIN ARCUS c ON d.IDCUST = c.IDCUST
    WHERE (SWPAID = 0)
    AND c.IDCUST = ?
"""

import adata

for index_code in ["000905", "000300"]:
    df = adata.stock.info.index_constituent(index_code=index_code)
    df.to_csv(f"{index_code}.csv")

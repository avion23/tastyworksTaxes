from tastyworksTaxes.position import PositionType

ASSET_DEFINITIONS = {
    PositionType.stock: {
        'EQUITY_ETF': {
            'symbols': {'SCHG', 'TECL', 'QQQ', 'SPY', 'VTI', 'VXUS'},
            'properties': {'teilfreistellung_pct': 30},
            'tax_category': 'KAP-INV'
        },
        'BOND_ETF': {
            'symbols': {'PULS', 'VGSH', 'ICSH', 'TLT', 'BND', 'AGG'},
            'properties': {'teilfreistellung_pct': 0},
            'tax_category': 'KAP-INV'
        },
        'MIXED_FUND_ETF': {
            'symbols': {'AOM', 'AOR', 'AOK', 'AOA'},
            'properties': {'teilfreistellung_pct': 15},
            'tax_category': 'KAP-INV'
        },
        'REAL_ESTATE_ETF': {
            'symbols': {'VNQ', 'IYR', 'VNQI', 'RWR'},
            'properties': {'teilfreistellung_pct': 60},
            'tax_category': 'KAP-INV'
        },
        'CRYPTO': {
            'symbols': lambda s: s.endswith('/USD') or s.endswith('/EUR') or s in {'BTC', 'ETH', 'DOGE'},
            'properties': {},
            'tax_category': 'SO'
        }
    }
}
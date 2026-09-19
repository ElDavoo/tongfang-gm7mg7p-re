namespace MyControlCenter.MyRgbKeyboard;

internal class COLOR_CELL
{
	internal uint Index;

	internal byte R;

	internal byte G;

	internal byte B;

	internal byte R_Level;

	internal byte G_Level;

	internal byte B_Level;

	internal COLOR_CELL(uint _index, byte _r, byte _g, byte _b, byte _r_level, byte _g_level, byte _b_level)
	{
		Index = _index;
		R = _r;
		G = _g;
		B = _b;
		R_Level = _r_level;
		G_Level = _g_level;
		B_Level = _b_level;
	}

	public override string ToString()
	{
		return string.Format("Index: {0}, RGB ({1}, {2}, {3}), level ({4}, {5}, {6}) (0x{7},0x{8},0x{9})", Index, R.ToString().PadLeft(3), G.ToString().PadLeft(3), B.ToString().PadLeft(3), R_Level.ToString().PadLeft(2), G_Level.ToString().PadLeft(2), B_Level.ToString().PadLeft(2), R_Level.ToString("X2").PadLeft(2, '0'), G_Level.ToString("X2").PadLeft(2, '0'), B_Level.ToString("X2").PadLeft(2, '0'));
	}
}

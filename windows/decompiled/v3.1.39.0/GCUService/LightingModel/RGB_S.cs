namespace LightingModel;

public struct RGB_S
{
	public uint ID;

	public byte R;

	public byte G;

	public byte B;

	public RGB_S(uint _id, byte _r, byte _g, byte _b)
	{
		ID = _id;
		R = _r;
		G = _g;
		B = _b;
	}
}

namespace LightingModel;

public struct RGBKB_Color
{
	public bool isCircular;

	public uint ColorBlocks;

	public RGB_S[] ColorBuffer;

	public RGBKB_Color(bool bCircular, uint Length)
	{
		isCircular = bCircular;
		ColorBlocks = Length;
		ColorBuffer = new RGB_S[Length];
		for (uint num = 0u; num < Length; num++)
		{
			ColorBuffer[num].ID = num;
			ColorBuffer[num].R = 0;
			ColorBuffer[num].G = 0;
			ColorBuffer[num].B = 0;
		}
	}
}

namespace MyControlCenter;

internal static class RGBLightBarTable_QC
{
	private static uint _R_PWM_Lev0 = 0u;

	private static uint _R_PWM_Lev1 = 4u;

	private static uint _R_PWM_Lev2 = 8u;

	private static uint _R_PWM_Lev3 = 12u;

	private static uint _R_PWM_Lev4 = 16u;

	private static uint _R_PWM_Lev5 = 20u;

	private static uint _R_PWM_Lev6 = 24u;

	private static uint _R_PWM_Lev7 = 28u;

	private static uint _R_PWM_Lev8 = 32u;

	private static uint _R_PWM_Lev9 = 36u;

	private static uint _G_PWM_Lev0 = 0u;

	private static uint _G_PWM_Lev1 = 4u;

	private static uint _G_PWM_Lev2 = 8u;

	private static uint _G_PWM_Lev3 = 12u;

	private static uint _G_PWM_Lev4 = 16u;

	private static uint _G_PWM_Lev5 = 20u;

	private static uint _G_PWM_Lev6 = 24u;

	private static uint _G_PWM_Lev7 = 28u;

	private static uint _G_PWM_Lev8 = 32u;

	private static uint _G_PWM_Lev9 = 36u;

	private static uint _B_PWM_Lev0 = 0u;

	private static uint _B_PWM_Lev1 = 4u;

	private static uint _B_PWM_Lev2 = 8u;

	private static uint _B_PWM_Lev3 = 12u;

	private static uint _B_PWM_Lev4 = 16u;

	private static uint _B_PWM_Lev5 = 20u;

	private static uint _B_PWM_Lev6 = 24u;

	private static uint _B_PWM_Lev7 = 28u;

	private static uint _B_PWM_Lev8 = 32u;

	private static uint _B_PWM_Lev9 = 36u;

	public static void Init(int nProjectID)
	{
	}

	public static ulong GetTable(string Table, uint InputLevel)
	{
		ulong result = 0uL;
		switch (Table)
		{
		case "Red":
			switch (InputLevel)
			{
			case 0u:
				result = _R_PWM_Lev0;
				break;
			case 1u:
				result = _R_PWM_Lev1;
				break;
			case 2u:
				result = _R_PWM_Lev2;
				break;
			case 3u:
				result = _R_PWM_Lev3;
				break;
			case 4u:
				result = _R_PWM_Lev4;
				break;
			case 5u:
				result = _R_PWM_Lev5;
				break;
			case 6u:
				result = _R_PWM_Lev6;
				break;
			case 7u:
				result = _R_PWM_Lev7;
				break;
			case 8u:
				result = _R_PWM_Lev8;
				break;
			case 9u:
				result = _R_PWM_Lev9;
				break;
			}
			break;
		case "Green":
			switch (InputLevel)
			{
			case 0u:
				result = _G_PWM_Lev0;
				break;
			case 1u:
				result = _G_PWM_Lev1;
				break;
			case 2u:
				result = _G_PWM_Lev2;
				break;
			case 3u:
				result = _G_PWM_Lev3;
				break;
			case 4u:
				result = _G_PWM_Lev4;
				break;
			case 5u:
				result = _G_PWM_Lev5;
				break;
			case 6u:
				result = _G_PWM_Lev6;
				break;
			case 7u:
				result = _G_PWM_Lev7;
				break;
			case 8u:
				result = _G_PWM_Lev8;
				break;
			case 9u:
				result = _G_PWM_Lev9;
				break;
			}
			break;
		case "Blue":
			switch (InputLevel)
			{
			case 0u:
				result = _B_PWM_Lev0;
				break;
			case 1u:
				result = _B_PWM_Lev1;
				break;
			case 2u:
				result = _B_PWM_Lev2;
				break;
			case 3u:
				result = _B_PWM_Lev3;
				break;
			case 4u:
				result = _B_PWM_Lev4;
				break;
			case 5u:
				result = _B_PWM_Lev5;
				break;
			case 6u:
				result = _B_PWM_Lev6;
				break;
			case 7u:
				result = _B_PWM_Lev7;
				break;
			case 8u:
				result = _B_PWM_Lev8;
				break;
			case 9u:
				result = _B_PWM_Lev9;
				break;
			}
			break;
		}
		return result;
	}
}

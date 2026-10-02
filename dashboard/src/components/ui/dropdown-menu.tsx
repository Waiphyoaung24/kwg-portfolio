import * as React from 'react';
import { Menu } from '@base-ui/react/menu';
import { CheckIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

// Base UI menu composition from https://base-ui.com/react/components/menu.
export const DropdownMenu = Menu.Root;
export const DropdownMenuTrigger = Menu.Trigger;
export const DropdownMenuRadioGroup = Menu.RadioGroup;

export function DropdownMenuContent({className,children,...props}: React.ComponentProps<typeof Menu.Popup>){
 return <Menu.Portal><Menu.Positioner className="dropdown-positioner" side="top" align="start" sideOffset={8} collisionPadding={16}><Menu.Popup data-slot="dropdown-menu-content" className={cn('dropdown-content',className)} {...props}>{children}</Menu.Popup></Menu.Positioner></Menu.Portal>;
}
export function DropdownMenuRadioItem({className,children,...props}: React.ComponentProps<typeof Menu.RadioItem>){
 return <Menu.RadioItem data-slot="dropdown-menu-radio-item" className={cn('dropdown-item',className)} closeOnClick {...props}><span className="dropdown-indicator" aria-hidden="true"><Menu.RadioItemIndicator><CheckIcon/></Menu.RadioItemIndicator></span>{children}</Menu.RadioItem>;
}

import {
  Toggletip,
  ToggletipButton,
  ToggletipContent,
} from '@carbon/react'
import { Information } from '@carbon/icons-react'

export function SectionHelp({ align = 'bottom', label = 'Show more information', title, children }) {
  return (
    <Toggletip align={align}>
      <ToggletipButton className="section-help-trigger" label={label}>
        <Information size={16} />
      </ToggletipButton>
      <ToggletipContent>
        <div className="section-help-content">
          {title && <strong>{title}</strong>}
          <p>{children}</p>
        </div>
      </ToggletipContent>
    </Toggletip>
  )
}

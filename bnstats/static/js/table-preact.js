import { h, render, createContext } from 'https://cdn.skypack.dev/preact'
import { useState, useEffect, useContext } from 'https://cdn.skypack.dev/preact/hooks'
import htm from 'https://unpkg.com/htm?module'

const html = htm.bind(h)
const mountTarget = document.getElementById('listingContent')
const genres = JSON.parse(mountTarget.dataset.genres)
const langs = JSON.parse(mountTarget.dataset.langs)
const diffs = JSON.parse(mountTarget.dataset.diffs)
const users = JSON.parse(mountTarget.dataset.users)
const counts = JSON.parse(mountTarget.dataset.counts)
const evalCounts = JSON.parse(mountTarget.dataset.evalcounts)

const keyTransform = {
    genre: 'genre_favor',
    language: 'lang_favor',
    diff: 'topdiff_favor',
    length: 'length_favor',
    size: 'size_favor',
    mode: 'modes',
}

const FilterCtx = createContext(null)

function FilterContextProvider(props) {
    const [filter, setFilter] = useState('')
    return html`<${FilterCtx.Provider} value=${{ filter, setFilter }}>${props.children}</${FilterCtx.Provider}>`
}

function UserLabels(props) {
    const { user } = props
    return html`
        ${user.genre_favor &&
        user.genre_favor.map((genre) => html` <a class="ui label">Genre: ${genre.replace(' ', '')}</a> `)}
        ${user.lang_favor && user.lang_favor.map((lang) => html` <a class="ui label">Language: ${lang}</a> `)}
        ${user.length_favor && html`<a class="ui label">Length: ${user.length_favor}</a>`}
        ${user.size_favor && html`<a class="ui label">Size: ${user.size_favor}</a>`}
        ${user.topdiff_favor &&
        user.topdiff_favor.map((diff) => html` <a class="ui label">Top Difficulty: ${diff}</a> `)}
        ${user.modes && user.modes.map((mode) => html` <a class="ui label">Mode: ${mode}</a> `)}
    `
}

function ApplyButtons(props) {
    const { setFilter } = useContext(FilterCtx)

    const onApply = (e) => {
        e.preventDefault()
        let filters = $('#filterSelect').serializeArray()
        let formattedFilters = {}
        for (let i = 0; i < filters.length; i++) {
            let obj = filters[i]
            let key = keyTransform[obj.name]
            if (key in formattedFilters) {
                formattedFilters[key].push(obj.value)
            } else {
                formattedFilters[key] = [obj.value]
            }
        }

        setFilter(formattedFilters)
    }

    const onReset = (e) => {
        e.preventDefault()
        $('.dropdown').dropdown('clear')
        onApply(e)
    }

    return html` <div>
        <button class="ui inverted basic button" onClick=${onApply}>Apply filters</button>
        <button class="ui inverted basic red button" onClick=${onReset}>Reset filters</button>
    </div>`
}

function FilterArea(props) {
    return html`
        <form id="filterSelect" class="ui inverted form" onsubmit="return false">
            <div class="field">
                <label>Genre</label>
                <select multiple name="genre" class="ui dropdown">
                    <option value="">Select Genre</option>
                    ${genres.slice(2).map((genre) => html`<option key=${genre} value=${genre}>${genre}</option>`)}
                </select>
            </div>

            <div class="field">
                <label>Language</label>
                <select multiple name="language" class="ui dropdown">
                    <option value="">Select Language</option>
                    ${langs.slice(2).map((lang) => html`<option key=${lang} value=${lang}>${lang}</option>`)}
                </select>
            </div>

            <div class="field">
                <label>Difficulty</label>
                <select multiple name="diff" class="ui dropdown">
                    <option value="">Select Difficulty</option>
                    ${diffs.slice(2).map((diff) => html`<option key=${diff} value=${diff}>${diff}</option>`)}
                </select>
            </div>

            <div class="field">
                <label>Length</label>
                <select multiple name="length" class="ui dropdown">
                    <option value="">Select Length</option>
                    <option value="Short">Short</option>
                    <option value="Medium">Medium</option>
                    <option value="Long">Long</option>
                </select>
            </div>

            <div class="field">
                <label>Size</label>
                <select multiple name="size" class="ui dropdown">
                    <option value="">Select Size</option>
                    <option value="Small">Small</option>
                    <option value="Medium">Medium</option>
                    <option value="Big">Big</option>
                </select>
            </div>

            <div class="field">
                <label>Mode</label>
                <select multiple name="mode" class="ui dropdown">
                    <option value="">Select mode</option>
                    <option value="osu">osu!</option>
                    <option value="taiko">Taiko</option>
                    <option value="catch">Catch</option>
                    <option value="mania">Mania</option>
                </select>
            </div>

            <${ApplyButtons} />

            <div class="ui blue inverted message">
                <p>
                    Operation in filters is AND for each type, and OR for each value. For example: (Anime || Rock) &&
                    (Japanese || English)
                </p>
            </div>
        </form>
    `
}

function UserTable(props) {
    const [filteredUsers, setFilteredUsers] = useState(users)
    const [sortedUsers, setSortedUsers] = useState(users)
    const [sortKey, setSortKey] = useState('username')
    const [ascending, setAscending] = useState(true)

    const { filter } = useContext(FilterCtx)
    const { showFormer, filterDay } = props

    useEffect(() => {
        let filtered = users.filter((user) => user.isBn || user.isNat || showFormer)

        for (let [key, valToFilter] of Object.entries(filter)) {
            filtered = filtered.filter((user) => {
                if (!user[key]) return false

                for (let val of valToFilter) {
                    val = val.replace(' ', '_')
                    if (user[key] === val || user[key].indexOf(val) !== -1) return true
                }
                return false
            })
        }

        setFilteredUsers(filtered)
    }, [filter, showFormer])

    useEffect(() => {
        let sorted = [...filteredUsers].sort((a, b) => {
            if (sortKey == 'username') {
                return a.username.localeCompare(b.username)
            }

            if (sortKey == 'count') {
                if (filterDay == -1) {
                    return counts[a.username] - counts[b.username]
                } else {
                    return evalCounts[a.username] - evalCounts[b.username]
                }
            }
        })

        if (!ascending) sorted = sorted.reverse()
        setSortedUsers(sorted)
    }, [filteredUsers, sortKey, ascending, filterDay])

    const openUser = (user) => window.open('/users/' + user.osuId)

    return html`
        <div class="table-wrapper">
            <table class="ui celled padded inverted unstackable selectable table">
                <thead>
                    <tr>
                        <th
                            onClick=${() => {
                                if (sortKey == 'username') {
                                    setAscending(!ascending)
                                } else {
                                    setSortKey('username')
                                    setAscending(true)
                                }
                            }}
                        >
                            Username
                        </th>
                        <th class="no-sort">Attributes</th>
                        <th class="no-sort">Game mode</th>
                        <th
                            class="number"
                            onClick=${() => {
                                if (sortKey == 'count') {
                                    setAscending(!ascending)
                                } else {
                                    setSortKey('count')
                                    setAscending(false)
                                }
                            }}
                        >
                            Nominations
                        </th>
                    </tr>
                </thead>
                <tbody>
                    ${sortedUsers.map(
                        (user, i) => html`
                            <tr
                                key=${user._id}
                                style="${!user.isBn && !user.isNat && 'opacity: 0.5'}"
                                onClick=${() => openUser(user)}
                            >
                                <td>${user.username}</td>
                                <td><${UserLabels} user=${user} /></td>
                                <td>${user.modes.join(', ')}</td>

                                <td>
                                    ${counts[user.username]}
                                    <span class="ui small text" data-tooltip="Last 90 days">
                                        (${evalCounts[user.username]})
                                    </span>
                                </td>
                            </tr>
                        `
                    )}
                </tbody>
            </table>
        </div>
    `
}

function UserListing(props) {
    const [filterDay, setFilterDay] = useState(-1)
    const [showFormer, setShowFormer] = useState(false)

    return html` <div class="ui list">
        <div class="ui horizontal list" style="padding-top: 10px; padding-bottom: 10px;">
            <div class="item">Sort nominations from</div>
            <div class="item">
                <div class="ui buttons">
                    <button class="mini ui ${filterDay == -1 && 'active'} button" onClick=${() => setFilterDay(-1)}>
                        All time
                    </button>
                    <button class="mini ui ${filterDay == 90 && 'active'} button" onClick=${() => setFilterDay(90)}>
                        90 days
                    </button>
                </div>
            </div>
        </div>
        <br />
        <!-- 
        <div class="ui horizontal list" style="padding-bottom: 10px;">
            <div class="item">Show former BN/NAT/QAT</div>
            <div class="item">
                <div class="ui buttons">
                    <button class="mini ui ${showFormer && 'active'} button" onClick=${() => setShowFormer(true)}>
                        Yes
                    </button>
                    <button class="mini ui ${!showFormer && 'active'} button" onClick=${() => setShowFormer(false)}>
                        No
                    </button>
                </div>
            </div>
        </div>
        -->
        <${UserTable} filterDay=${filterDay} showFormer=${showFormer} />
    </div>`
}

function UserListingApp(props) {
    return html`
        <${FilterContextProvider}>
            <${FilterArea} />
            <${UserListing} />
        </${FilterContextProvider}>
    `
}

render(html`<${UserListingApp} />`, mountTarget)
